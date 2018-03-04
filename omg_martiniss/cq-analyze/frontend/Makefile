
.PHONY: build
build: $(main_file)
	python build.py build

main_file = build/es6-bundled/elements/analyze-app.html
$(main_file): elements/* polymer.json
	polymer build

deploy: build
	gae.py upload

serve: dev
	gae.py server

.PHONY: dev
dev:
	@python build.py dev
