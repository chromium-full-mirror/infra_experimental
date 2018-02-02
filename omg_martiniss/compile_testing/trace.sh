#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
$DIR/ninja_log_trace_viewer --filename $1 -port 12345 -trace_viewer_tmpl $DIR/trace-viewer.html
