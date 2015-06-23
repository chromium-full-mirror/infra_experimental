#
# Source this file to set up Go environment.
#

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

SRC="${DIR}"
VENDOR="${DIR}/.vendor"

export GOPATH="${SRC}:${VENDOR}"
