# CQ Analyzer

This app is a glorified set of BQ queries. It's there to make analysis faster,
so we can understand what's slow on our builders, and fix it.

This is semi expected to be sym linked to infra.git/go/src/infra/appengine
You have to run `go generate` when you change the api stuff from that directory.

In infra/go run the following to activate the go environment:
eval `./env.py`

Use `make deploy` in `frontend` to deploy. This compiles the polymer code
and rewrites the app.yaml to serve the minified html.

To run a local instance:
`make server`

To run tests:
What are tests?
