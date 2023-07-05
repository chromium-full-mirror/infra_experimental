#!/bin/bash

ADDR=${TEST_TARGET_ADDR:-http://127.0.0.1:8080}
TOKEN=$(luci-auth token -use-id-token)

curl -H "Authorization: Bearer ${TOKEN}" "${ADDR}"
curl -H "Authorization: Bearer ${TOKEN}" "${ADDR}/group/mdb/chrome-troopers"
curl -H "Authorization: Bearer ${TOKEN}" "${ADDR}/group/administrators"
curl -H "Authorization: Bearer ${TOKEN}" "${ADDR}/group/unknown"

curl -H "Authorization: Bearer ${TOKEN}" "${ADDR}/permission/buildbucket.builds.get/infra:loadtest"
curl -H "Authorization: Bearer ${TOKEN}" "${ADDR}/permission/buildbucket.builds.get/unknown:unknown"
