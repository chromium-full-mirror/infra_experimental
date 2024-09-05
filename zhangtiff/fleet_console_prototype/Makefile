# Copyright 2024 The LUCI Authors. All rights reserved.
# Use of this source code is governed under the Apache License, Version 2.0
# that can be found in the LICENSE file.

# All commands here are exclusively for local development. Images produced here
# shouldn't really be pushed anywhere.

build-binary:
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o ./docker .

build-image-local: build-binary
	docker build -t helloworld ./docker

run-image: build-image-local
	docker run --rm \
		-p 8800:8800 \
		-p 8900:8900 \
		-v ~/.config/chrome_infra/auth:/tokens \
		us-docker.pkg.dev/fleet-console-prototype/fleet/helloworld:latest \
			-http-addr :8800 \
			-admin-addr :8900 \
			-token-cache-dir /tokens
			-project fleet-console-prototype

build-image-prod:
	docker build ./docker --tag  us-docker.pkg.dev/fleet-console-prototype/fleet/helloworld:latest --platform linux/amd64

push-image-prod:
	docker push us-docker.pkg.dev/fleet-console-prototype/fleet/helloworld:latest

deploy: build-image-prod push-image-prod
	gcloud run deploy helloworld \
		--project=fleet-console-prototype \
		--region=us-west1 \
		--port=8800 \
		--args="--http-addr=:8800" \
		--image=us-docker.pkg.dev/fleet-console-prototype/fleet/helloworld:latest

gen-proto-client:
	sh scripts/gen_client_proto.sh

gen-proto-go:
	go generate ./...

gen-proto: gen-proto-go gen-proto-client
