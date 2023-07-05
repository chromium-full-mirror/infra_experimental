#!/bin/bash

PROTO_ROOT=~/infra-superproject/infra/go/src/go.chromium.org

./pyvenv/bin/python3 -m grpc_tools.protoc \
    -I ${PROTO_ROOT} \
    -I ${PROTO_ROOT}/luci/common/proto/googleapis \
    --python_out=. \
    --pyi_out=. \
    --grpc_python_out=. \
    ${PROTO_ROOT}/luci/common/proto/sidecar/*.proto
