#!/bin/bash

BUILDER=%s
#BUILDER="linux_chromium_rel_ng"
MACHINE=%s
#MACHINE="test-machine"
NAME=%s
#NAME="test-name"

sudo gcloud docker -- pull gcr.io/martiniss-test-compile-time/$BUILDER
for RUN in {1..%s}; do
  BOT_NAME="compile_bot_$RUN"
  sudo docker run -itd --name $BOT_NAME gcr.io/martiniss-test-compile-time/$BUILDER --builder $BUILDER %s
  sudo docker wait $BOT_NAME
  sudo docker cp $BOT_NAME:/home/compile/output /home/martiniss/output_tmp
  echo "machine type: "$MACHINE >> /home/martiniss/output_tmp
  echo "run number "$RUN >> /home/martiniss/output_tmp
  cat /home/martiniss/output_tmp >> /home/martiniss/output
  sudo docker cp $BOT_NAME:/home/compile/ninja_log /home/martiniss/ninja_log_tmp
  echo "run number "$RUN >> /home/martiniss/ninja_log_tmp
  cat /home/martiniss/ninja_log_tmp >> /home/martiniss/ninja_log
  sudo docker cp $BOT_NAME:/home/compile/stdout /home/martiniss/stdout_tmp
  cat /home/martiniss/stdout_tmp >> /home/martiniss/stdout
  echo "run number "$RUN >> /home/martiniss/stdout_tmp

  sudo docker container prune -f
done

sudo gsutil cp /home/martiniss/output gs://martiniss-compile-time-data/$BUILDER/results_$NAME
sudo gsutil cp /home/martiniss/ninja_log gs://martiniss-compile-time-data/$BUILDER/results_ninja_log_$NAME
sudo gsutil cp /home/martiniss/stdout gs://martiniss-compile-time-data/$BUILDER/stdout_$NAME
sudo shutdown now
