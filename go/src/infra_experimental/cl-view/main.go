package main

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"strconv"
	"strings"
	"time"

	"go.chromium.org/luci/common/sync/parallel"
	"golang.org/x/oauth2"

	"go.chromium.org/luci/server/router"

	"cloud.google.com/go/spanner"
	"go.chromium.org/luci/auth"
	"go.chromium.org/luci/common/logging"
	"go.chromium.org/luci/common/logging/gologger"
	"go.chromium.org/luci/hardcoded/chromeinfra"
	"google.golang.org/api/option"
)

func main() {
	ctx := context.Background()
	ctx = gologger.StdConfig.Use(ctx)

	opts := chromeinfra.DefaultAuthOptions()
	opts.Scopes = []string{"https://www.googleapis.com/auth/cloud-platform"}
	a := auth.NewAuthenticator(ctx, auth.InteractiveLogin, opts)
	ts, err := a.TokenSource()
	if err != nil {
		panic(err)
	}

	r := router.NewWithRootContext(ctx)
	base := router.MiddlewareChain{}

	handler := ChangeHandler{
		TokenSource: ts,
	}
	r.GET("/c/:host/:change/:patch", base, handler.HandleChange)
	r.POST("/rpc/stats", base, handler.Stats)

	serveDir(r, base, "node_modules")
	serveDir(r, base, "dist")

	logging.Infof(ctx, "listening at :8090")
	log.Fatal(http.ListenAndServe(":8090", r))
}

func serveDir(r *router.Router, mw router.MiddlewareChain, relDir string) {
	server := http.StripPrefix("/"+relDir, http.FileServer(http.Dir(relDir)))
	r.GET(fmt.Sprintf("/%s/*rest", relDir), mw, func(c *router.Context) {
		server.ServeHTTP(c.Writer, c.Request)
	})

}

type ChangeHandler struct {
	TokenSource oauth2.TokenSource
}

func (h *ChangeHandler) Stats(ctx *router.Context) {
	var request struct {
		InvocationID string
	}
	if err := json.NewDecoder(ctx.Request.Body).Decode(&request); err != nil {
		http.Error(ctx.Writer, err.Error(), http.StatusBadRequest)
		return
	}

	spn, err := h.spannerClient(ctx.Context)
	if err != nil {
		panic(err)
	}
	defer spn.Close()

	txn := spn.ReadOnlyTransaction()
	defer txn.Close()

	var stats struct {
		TotalTests    int64 `json:"totalTests"`
		TotalVariants int64 `json:"totalVariants"`
		TotalTestRuns int64 `json:"totalTestRuns"`
	}

	err = txn.Query(ctx.Context, spanner.Statement{
		SQL: `
					SELECT
						COUNT(DISTINCT TestName) TotalTests,
						COUNT(DISTINCT VariantHash) TotalVariants,
						COUNT(*) TotalTestRuns
					FROM Inclusions incl
					JOIN TestRuns tr ON incl.IncludedInvocationId = tr.InvocationId
					WHERE incl.InvocationId = @AttemptInvocationID
				`,
		Params: map[string]interface{}{
			"AttemptInvocationID": request.InvocationID,
		},
	}).Do(func(r *spanner.Row) error {
		return r.ToStruct(&stats)
	})
	if err != nil {
		panic(err)
	}

	if err = json.NewEncoder(ctx.Writer).Encode(&stats); err != nil {
		panic(err)
	}
}

func (h *ChangeHandler) spannerClient(ctx context.Context) (*spanner.Client, error) {
	return spanner.NewClient(
		ctx, "projects/luci-test-results-dev/instances/test-results/databases/test-results",
		option.WithTokenSource(h.TokenSource),
		option.WithQuotaProject("luci-test-results-dev"),
	)
}

func (h *ChangeHandler) HandleChange(ctx *router.Context) {
	tag := fmt.Sprintf("cq-attempt/gerrit-patch/%s/%s/%s", ctx.Params.ByName("host"), ctx.Params.ByName("change"), ctx.Params.ByName("patch"))
	logging.Infof(ctx.Context, "using invocation tag %q, full is %q", tag, hashed(tag))

	spn, err := h.spannerClient(ctx.Context)
	if err != nil {
		panic(err)
	}
	defer spn.Close()

	txn := spn.ReadOnlyTransaction()
	defer txn.Close()

	info, err := h.loadChangeInfo(ctx.Context, txn, tag)
	if err != nil {
		http.Error(ctx.Writer, err.Error(), http.StatusInternalServerError)
		return
	}

	infoJSON, err := json.Marshal(info)
	if err != nil {
		http.Error(ctx.Writer, err.Error(), http.StatusInternalServerError)
		return
	}

	err = indexTemplate.Execute(ctx.Writer, map[string]interface{}{
		"ChangeInfoJSON": template.JS(string(infoJSON)),
	})
	if err != nil {
		panic(err)
	}
}

type ChangeInfo struct {
	CQAttempts []*CQAttempt `json:"cqAttempts"`
}

type CQAttempt struct {
	InvocationId string    `json:"invocationId"`
	Started      time.Time `json:"started"`

	InterestingTestVariants []*InterestingTestVariant `json:"interestingTestVariants"`
	Exonerations            []*Exoneration            `json:"exonerations"`

	Tests map[string]*Test `json:"tests"`
}

type Test struct {
	Variants map[string]*TestVariant `json:"variants"`
}

type TestVariant struct {
	Def  []string   `json:"def"`
	Runs []*TestRun `json:"runs"`
}

type TestRun struct {
	Status string `json:"status"`
}

var statusByNumber = []string{
	0: "UNKNOWN",
	1: "PASS",
	2: "FAIL",
	3: "CRASH",
	4: "ABORT",
	5: "SKIP",
	6: "TIMEOUT",
}

type InterestingTestVariant struct {
	TestName    string   `json:"testName"`
	VariantHash string   `json:"variantHash"`
	VariantDef  []string `json:"variantDef"`
}

type Exoneration struct {
	TestName            string `json:"testName"`
	VariantHash         string `json:"variantHash"`
	ExplanationMarkdown string `json:"explanationMarkdown"`
}

func (*ChangeHandler) loadChangeInfo(ctx context.Context, txn *spanner.ReadOnlyTransaction, tag string) (*ChangeInfo, error) {
	ret := &ChangeInfo{}

	err := txn.Query(ctx, spanner.Statement{
		SQL: `
			SELECT DISTINCT InvocationId
			FROM InvocationTags
			WHERE Tag = @Tag
		`,
		Params: map[string]interface{}{
			"Tag": hashed(tag),
		},
	}).Do(func(r *spanner.Row) error {
		attempt := &CQAttempt{}
		if err := r.Column(0, &attempt.InvocationId); err != nil {
			return err
		}
		parts := strings.Split(attempt.InvocationId, "/")
		ts, err := strconv.ParseInt(parts[len(parts)-1], 10, 64)
		if err != nil {
			return err
		}
		attempt.Started = time.Unix(ts/1000, 0)

		ret.CQAttempts = append(ret.CQAttempts, attempt)
		return nil
	})
	if err != nil {
		return nil, err
	}

	for _, a := range ret.CQAttempts {
		logging.Infof(ctx, "Attempt: %s", a.InvocationId)
	}
	if len(ret.CQAttempts) == 0 {
		return ret, nil
	}

	latest := ret.CQAttempts[len(ret.CQAttempts)-1]
	latest.Tests = map[string]*Test{}
	start := time.Now()
	err = parallel.FanOutIn(func(work chan<- func() error) {
		// Load interesting test runs.
		work <- func() error {
			return txn.Query(ctx, spanner.Statement{
				SQL: `
				SELECT tr.TestName, tr.VariantHash, tr.VariantDef, tr.Status
				FROM (
					SELECT itv.InvocationId, itv.TestName, itv.VariantHash
					FROM Inclusions incl
					JOIN InterestingTestVariants itv ON itv.InvocationId = incl.IncludedInvocationId
					JOIN TestRuns tr ON tr.InvocationId = itv.InvocationId AND tr.TestName = itv.TestName AND tr.VariantHash = itv.VariantHash
					WHERE incl.InvocationId = @AttemptInvocationID
					GROUP BY itv.InvocationId, itv.TestName, itv.VariantHash
					HAVING NOT LOGICAL_OR(Status = 1)

					EXCEPT DISTINCT

					SELECT ex.InvocationId, ex.TestName, ex.VariantHash
					FROM Inclusions incl
					JOIN Exonerations ex ON ex.InvocationId = incl.IncludedInvocationId
					WHERE incl.InvocationId = @AttemptInvocationID
				) intr
				JOIN TestRuns tr ON tr.InvocationId = intr.InvocationId AND tr.TestName = intr.TestName AND tr.VariantHash = intr.VariantHash
				ORDER BY TestName
	`,
				Params: map[string]interface{}{
					"AttemptInvocationID": latest.InvocationId,
				},
			}).Do(func(r *spanner.Row) error {
				var row struct {
					TestName    string
					VariantHash string
					VariantDef  []string
					Status      int64
				}
				if err := r.ToStruct(&row); err != nil {
					return err
				}

				test := latest.Tests[row.TestName]
				if test == nil {
					test = &Test{Variants: map[string]*TestVariant{}}
					latest.Tests[row.TestName] = test
				}
				variant := test.Variants[row.VariantHash]
				if variant == nil {
					variant = &TestVariant{
						Def: row.VariantDef,
					}
					test.Variants[row.VariantHash] = variant
				}
				variant.Runs = append(variant.Runs, &TestRun{
					Status: statusByNumber[int(row.Status)],
				})
				return nil
			})
		}

		work <- func() error {
			return txn.Query(ctx, spanner.Statement{
				SQL: `
					SELECT tr.TestName, tr.VariantHash, tr.VariantDef
					FROM (
						SELECT DISTINCT TestName
						FROM (
							SELECT itv.InvocationId, itv.TestName, itv.VariantHash
							FROM Inclusions incl
							JOIN InterestingTestVariants itv ON itv.InvocationId = incl.IncludedInvocationId
														JOIN TestRuns tr ON tr.InvocationId = itv.InvocationId AND tr.TestName = itv.TestName AND tr.VariantHash = itv.VariantHash
							WHERE incl.InvocationId = @AttemptInvocationID
							GROUP BY itv.InvocationId, itv.TestName, itv.VariantHash
							HAVING NOT LOGICAL_OR(Status = 1)

							EXCEPT DISTINCT

							SELECT ex.InvocationId, ex.TestName, ex.VariantHash
							FROM Inclusions incl
							JOIN Exonerations ex ON ex.InvocationId = incl.IncludedInvocationId
							WHERE incl.InvocationId = @AttemptInvocationID
						)
					) interesting
					JOIN@{FORCE_JOIN_ORDER=TRUE} (
						SELECT TestName, VariantHash, ANY_VALUE(VariantDef) VariantDef
						FROM Inclusions incl
						JOIN TestRuns tr ON tr.InvocationId = incl.IncludedInvocationId
						WHERE incl.InvocationId = @AttemptInvocationID
						GROUP BY TestName, VariantHash
					) tr ON tr.TestName = interesting.TestName
			`,
				Params: map[string]interface{}{
					"AttemptInvocationID": latest.InvocationId,
				},
			}).Do(func(r *spanner.Row) error {
				variant := &InterestingTestVariant{}
				latest.InterestingTestVariants = append(latest.InterestingTestVariants, variant)
				return r.ToStruct(variant)
			})
		}

		// Load exonerations
		work <- func() error {
			return txn.Query(ctx, spanner.Statement{
				SQL: `
					SELECT ex.TestName, ex.VariantHash, ex.ExplanationMarkdown
					FROM Inclusions incl
					JOIN Exonerations ex ON ex.InvocationId = incl.IncludedInvocationId
					WHERE incl.InvocationId = @AttemptInvocationID
				`,
				Params: map[string]interface{}{
					"AttemptInvocationID": latest.InvocationId,
				},
			}).Do(func(r *spanner.Row) error {
				ex := &Exoneration{}
				latest.Exonerations = append(latest.Exonerations, ex)
				return r.ToStruct(ex)
			})
		}
	})
	if err != nil {
		return nil, err
	}
	logging.Infof(ctx, "took %s", time.Now().Sub(start))
	return ret, nil
}

func hashed(s string) string {
	h := sha256.Sum256([]byte(s))
	return fmt.Sprintf("%s_%s", hex.EncodeToString(h[:]), s)
}

var indexTemplate = template.Must(template.New("index").Parse(`
<!DOCTYPE html>

<html lang="en">
<head>
  <meta name="description" content="cl-page">
  <meta name="theme-color" content="#ffffff">
  <meta name="viewport"
  content="width=device-width, initial-scale=1.0">
  <meta http-equiv="X-UA-Compatible" content="ie=edge">
  <meta charset="UTF-8">

  <link rel="manifest" href="/manifest.json">
  <title>cl-page</title>

  <script src="/node_modules/material-components-web/dist/material-components-web.min.js"></script>
  <link rel="stylesheet" href="https://fonts.googleapis.com/icon?family=Material+Icons">
  <script type="module" src="/dist/main.js"></script>
</head>
<body>
	<cl-page changeinfo="{{.ChangeInfoJSON}}"></cl-page>
</body>
`))
