#!/bin/bash
for i in $(seq 0 $(($1-1)))
do
DISK_NAME=kafka-disk$i
DISK_SIZE=200GB
ZONE=us-central1-a

gcloud compute disks create --size=$DISK_SIZE --zone=$ZONE $DISK_NAME
gcloud compute instances attach-disk --zone=$ZONE --disk=$DISK_NAME --device-name temp-data k8s-kafka-cluster-master
gcloud compute ssh --zone=$ZONE k8s-kafka-cluster-master \
  --command "sudo mkdir -p /mnt/tmp && sudo /usr/share/google/safe_format_and_mount /dev/disk/by-id/google-temp-data /mnt/tmp"
gcloud compute instances detach-disk --zone=$ZONE --disk $DISK_NAME k8s-kafka-cluster-master
done

