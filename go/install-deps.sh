#!/bin/bash

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

SRC="${DIR}/src"
VENDOR="${DIR}/.vendor"

export GOPATH="${VENDOR}"
mkdir -p "${VENDOR}"
rsync -av --delete "${SRC}" "${VENDOR}"

cd "${VENDOR}"
go get ./...
