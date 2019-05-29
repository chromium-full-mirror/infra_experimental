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
	r.GET("/cl/:host/:change", base, handler.Handle)

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

func (h *ChangeHandler) Handle(ctx *router.Context) {
	tag := fmt.Sprintf("cq-attempets/gerrit-change/%s/%s", ctx.Params.ByName("host"), ctx.Params.ByName("change"))

	spn, err := spanner.NewClient(
		ctx.Context, "projects/luci-test-results-dev/instances/test-results/databases/test-results",
		option.WithTokenSource(h.TokenSource),
		option.WithQuotaProject("luci-test-results-dev"),
	)
	if err != nil {
		panic(err)
	}
	defer spn.Close()

	txn := spn.ReadOnlyTransaction()
	defer txn.Close()

	_ = tag
	// info, err := h.loadChangeInfo(ctx.Context, txn, tag)
	// if err != nil {
	// 	http.Error(ctx.Writer, err.Error(), http.StatusInternalServerError)
	// 	return
	// }
	info := &ChangeInfo{
		CQAttempts: []*CQAttempt{
			{
				InvocationId: "cq-attempt/gerrit-change/chromium-review.googlesource.com/1/2/10000",
			},
			{
				InvocationId:  "cq-attempt/gerrit-change/chromium-review.googlesource.com/1/2/20000",
				TotalTests:    100,
				TotalVariants: 200,
				TotalTestRuns: 300,
				InterestingTestVariants: []*InterestingTestVariant{
					{
						TestName:    "a|b|c",
						VariantHash: "deadbeef",
						VariantDef: []string{
							"os:linux",
							"gpu:ati",
						},
						Successes: 0,
						Failures:  3,
					},
				},
			},
		},
	}

	infoJSON, err := json.Marshal(info)
	if err != nil {
		http.Error(ctx.Writer, err.Error(), http.StatusInternalServerError)
		return
	}

	err = indexTemplate.Execute(ctx.Writer, map[string]interface{}{
		"ChangeInfo": template.JS(string(infoJSON)),
	})
	if err != nil {
		panic(err)
	}
}

type ChangeInfo struct {
	CQAttempts []*CQAttempt
}

type CQAttempt struct {
	InvocationId string

	TotalTests    int
	TotalVariants int
	TotalTestRuns int

	InterestingTestVariants []*InterestingTestVariant
	Exonerations            []*Exoneration
}

type InterestingTestVariant struct {
	TestName    string
	VariantHash string
	VariantDef  []string
	Successes   int
	Failures    int
}

type Exoneration struct {
	TestName            string
	VariantHash         string
	ExplanationMarkdown string
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
		ret.CQAttempts = append(ret.CQAttempts, attempt)
		return nil
	})
	if err != nil {
		return nil, err
	}

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
					JOIN TestRuns tr ON it.InvocationId = tr.InvocationId
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
					TODO: remove without patch
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

  <link rel="manifest" href="./manifest.json">
  <title>cl-page</title>

  <script src="/node_modules/material-components-web/dist/material-components-web.min.js"></script>
  <link rel="stylesheet" href="https://fonts.googleapis.com/icon?family=Material+Icons">
  <script type="module" src="/dist/main.js"></script>
</head>
<body>
	<cl-page changeinfo="{{.ChangeInfoJSON}}"></cl-page>
</body>
`))
