#!/bin/bash

if [ -z ${CLOUD_RUN_PROJECT} ]; then
    echo "Need CLOUD_RUN_PROJECT env var. See README.md."
    exit 1
fi
if [ -z ${CLOUD_RUN_SA} ]; then
    echo "Need CLOUD_RUN_SA env var. See README.md."
    exit 1
fi

# LUCI sidecar image to use, see builds at
# https://ci.chromium.org/ui/p/infra-internal/builders/prod/infra-docker-images-continuous
SIDECAR_IMAGE=gcr.io/chops-public-images-prod/luci/utils/sidecar:ci-2023.06.30-57951-8e1c1be

# Build the container image with python server code and tag it based on the
# inputs. We don't care about this tag really, just need something unique.
FLASK_IMAGE=$(cloudbuildhelper build \
    build/flask.yaml \
    -canonical-tag :inputs-hash \
    -render-to-stdout "{{.image.image}}:{{.image.tag}}")

# Prep a Cloud Run YAML spec referencing this container image.
CLOUD_RUN_SPEC=$(mktemp)
trap 'rm ${CLOUD_RUN_SPEC}' EXIT

# Few notable features:
#   1. Need BETA launch-stage for custom audiences and multi-container images.
#   2. Custom audience is needed to allow using tokens from `luci-auth`.
#   3. Startup probes are to make sure we serve only from healthy state.
cat << EOF > ${CLOUD_RUN_SPEC}
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: sidecar-helloworld
  annotations:
    run.googleapis.com/launch-stage: BETA
    run.googleapis.com/custom-audiences: '["446450136466-mj75ourhccki9fffaq8bc1e50di315po.apps.googleusercontent.com"]'
  labels:
    cloud.googleapis.com/location: us-west1
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/execution-environment: gen2
        run.googleapis.com/container-dependencies: '{"main":["sidecar"]}'
    spec:
      serviceAccountName: ${CLOUD_RUN_SA}
      containers:
        - name: main
          image: ${FLASK_IMAGE}
          env:
            - name: LUCI_SIDECARE_ADDR
              value: '127.0.0.1:8801'
          ports:
            - name: http1
              containerPort: 8080
          startupProbe:
            httpGet:
              path: /healthz
            failureThreshold: 10
            periodSeconds: 3
        - name: sidecar
          image: ${SIDECAR_IMAGE}
          args:
            - -grpc-addr=:8801
            - -container-image-id=${SIDECAR_IMAGE}
            - -auth-service-host=chrome-infra-auth-dev.appspot.com
            - -sidecar-subscribe-to-permission=buildbucket.builds.get
          startupProbe:
            grpc:
              port: 8801
            failureThreshold: 10
            periodSeconds: 3
EOF

# Deploy it.
gcloud beta run services replace ${CLOUD_RUN_SPEC} \
    --project ${CLOUD_RUN_PROJECT}
