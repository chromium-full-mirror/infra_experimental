.PHONY: init
init:
	npm ci

.PHONY: push
push:
	npx clasp push

.PHONY: test
test: push
	npx clasp run allTests

.PHONY: logs
logs:
	npx clasp logs

.PHONY: watch
watch:
	npx tsc -w --noEmit
