#!/bin/bash
# Run this script from its directory:
# cd scripts
# ./nat_setup.sh

# Respin the NAT box VM.
gcloud compute instances delete nat-box --zone us-central1-f
gcloud compute instances create nat-box --project chrome-infra-mon-proxy --machine-type f1-micro --zone us-central1-f --image ubuntu-14-04 --network default --can-ip-forward --tags nat --address proxy1 --metadata-from-file startup-script=nat_startup.sh 
# Refresh the NAT route.
# gcloud compute routes delete managed-vm-nat-route
# gcloud compute routes create managed-vm-nat-route --network default --destination-range 0.0.0.0/0 --next-hop-instance nat-box --next-hop-instance-zone us-central1-f --tags managed-gae-vm --priority 800
