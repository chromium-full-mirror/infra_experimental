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
	r.POST("/rpc/test-runs", base, handler.LoadRuns)

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

func (h *ChangeHandler) LoadRuns(ctx *router.Context) {
	var request struct {
		InvocationID string
		TestName     string
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

	type TestRun struct {
		VariantHash string   `json:"variantHash"`
		VariantDef  []string `json:"variantDef"`
		Status      int64    `json:"status"`
	}
	var runs []*TestRun

	err = txn.Query(ctx.Context, spanner.Statement{
		SQL: `
			SELECT
				tr.VariantHash,
				tr.VariantDef,
				tr.Status
			FROM Inclusions incl
			JOIN TestRuns tr ON tr.InvocationId = incl.IncludedInvocationId
			WHERE incl.InvocationId = @InvocationId
			  AND tr.TestName = @TestName
			AND RunID NOT LIKE '%without patch%'
		`,
		Params: map[string]interface{}{
			"InvocationId": request.InvocationID,
			"TestName":     request.TestName,
		},
	}).Do(func(r *spanner.Row) error {
		run := &TestRun{}
		runs = append(runs, run)
		return r.ToStruct(run)
	})
	if err != nil {
		http.Error(ctx.Writer, err.Error(), http.StatusInternalServerError)
		return
	}

	err = json.NewEncoder(ctx.Writer).Encode(map[string]interface{}{
		"runs": runs,
	})
	if err != nil {
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

	TotalTests    int64 `json:"totalTests"`
	TotalVariants int64 `json:"totalVariants"`
	TotalTestRuns int64 `json:"totalTestRuns"`

	InterestingTestVariants []*InterestingTestVariant `json:"interestingTestVariants"`
	Exonerations            []*Exoneration            `json:"exonerations"`
}

type InterestingTestVariant struct {
	TestName    string   `json:"testName"`
	VariantHash string   `json:"variantHash"`
	VariantDef  []string `json:"variantDef"`
	Successes   int64    `json:"successes"`
	Failures    int64    `json:"failures"`
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

	logging.Infof(ctx, "Found %d CQ Attempts", len(ret.CQAttempts))
	if len(ret.CQAttempts) == 0 {
		return ret, nil
	}

	latest := ret.CQAttempts[len(ret.CQAttempts)-1]
	return ret, parallel.FanOutIn(func(work chan<- func() error) {
		// Load stats
		work <- func() error {
			return txn.Query(ctx, spanner.Statement{
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
					"AttemptInvocationID": latest.InvocationId,
				},
			}).Do(func(r *spanner.Row) error {
				return r.ToStruct(latest)
			})
		}

		// Load interesting test variants
		work <- func() error {
			return txn.Query(ctx, spanner.Statement{
				SQL: `
					SELECT
						tr.TestName,
						tr.VariantHash,
						ANY_VALUE(tr.VariantDef) VariantDef,
						COUNTIF(Status = 1) successes,
						COUNTIF(Status IN (2, 3, 4)) failures
					FROM Inclusions incl
					JOIN InterestingTests it ON incl.IncludedInvocationId = it.InvocationId
					JOIN TestRuns tr ON it.InvocationId = tr.InvocationId AND it.TestName = tr.TestName
					WHERE incl.InvocationId = @AttemptInvocationID
					--TODO: remove without patch
					AND RunID NOT LIKE '%without patch%'
					GROUP BY tr.TestName, tr.VariantHash
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
