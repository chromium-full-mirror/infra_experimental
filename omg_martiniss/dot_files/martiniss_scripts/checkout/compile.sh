#!/bin/bash

go build -o checkout_binary checkout_cl.go
DIGEST=$(./checkout_binary getdigest)
echo $DIGEST
go build -o checkout_binary -ldflags "-X main.knownDigest=$DIGEST" checkout_cl.go
