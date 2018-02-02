#!/bin/bash

BUILDER=%s
#export BUILDER=linux_chromium_rel_ng
NAME=%s
#export NAME=test_bot

gcloud docker -- pull gcr.io/martiniss-test-compile-time/$BUILDER
BOT_NAME="compile_bot"
docker run -itd --name $BOT_NAME gcr.io/martiniss-test-compile-time/$BUILDER
docker wait $BOT_NAME
docker cp $BOT_NAME:/home/compile/output /home/martiniss/output
sudo gsutil cp /home/martiniss/output gs://martiniss-compile-time-data/$BUILDER/results_$NAME
docker cp $BOT_NAME:/home/compile/ninja_log /home/martiniss/ninja_log
sudo gsutil cp /home/martiniss/ninja_log gs://martiniss-compile-time-data/$BUILDER/results_ninja_log_$NAME
docker cp $BOT_NAME:/home/compile/stdout /home/martiniss/stdout
sudo gsutil cp /home/martiniss/stdout gs://martiniss-compile-time-data/$BUILDER/stdout_$NAME
sudo shutdown now
