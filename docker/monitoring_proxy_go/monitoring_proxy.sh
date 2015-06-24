#!/bin/bash
/monitoring_proxy \
  -monitoring_endpoint="https://chrome-infra-loadtest.appspot.com/test-auth" \
  -endpoint_auth auth_sa_json=/loadtest_creds.json \
  -pubsub_auth auth_sa_json=/pubsub_creds.json \
  -pubsub_project=chrome-infra-mon-pubsub \
  -pubsub_subscription="test-sub" \
  -workers=10 \
  -log_level=error
