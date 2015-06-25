#!/bin/bash
/monitoring_proxy \
  -endpoint_url="https://chrome-infra-loadtest.appspot.com/test-auth" \
  -endpoint_auth_path=/loadtest_creds.json \
  -pubsub_auth_path=/pubsub_creds.json \
  -pubsub_project=chrome-infra-mon-pubsub \
  -pubsub_subscription="test-sub" \
  -workers=20 \
  -log_level=error
