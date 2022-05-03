#!/bin/bash

CURDIR=$(dirname $(realpath $0))
PKG=@1
BINARY=$PKG".bin"

function compile() {
  echo "Compiling..."
  go build -o $BINARY $PKG
}

[[ -a $BINARY ]] || goluf $PKG $(stat -c %Y $BINARY) || compile

$BINARY "${@:2}"
