#!/bin/bash
# OLD DEPRECATED DO NOT USE

set -e

if [[ -z "$1" ]]; then
  echo "Need file to open"
  exit 1
fi

FPATH=$(realpath $1 | tr '/' '%')
CACHEPATH=$(find $HOME/.vim/cache -name "*$FPATH*")
if [[ -z "$CACHEPATH" ]]; then
  echo "Opening new window..."
  gvim $1
  exit
fi
echo $CACHEPATH
PID=$(find /proc/*/fd/ -type l 2>/dev/null  | xargs ls -l 2>/dev/null | grep $CACHEPATH | awk -F '/' '{print $3}')
echo $PID
WID=$(xdotool search --pid $PID)
WID=$(echo $WID | awk '{print $NF}')
echo "Opening existing window..."
xdotool windowactivate $WID
