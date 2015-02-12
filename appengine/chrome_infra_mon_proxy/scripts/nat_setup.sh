#!/bin/bash
# Run this script from its directory, to correctly pick up nat_startup.sh:
# cd scripts
# ./nat_setup.sh

PROJECT="chrome-infra-mon-proxy"
REGION="us-central1"
GAE_VM1_TAG="managed-gae-vm1"
GAE_VM2_TAG="managed-gae-vm2"
GAE_VM3_TAG="managed-gae-vm3"

function delete_instance {
    # delete_instance instance-name zone-name
    gcloud compute --project "$PROJECT" instances delete "$1" --zone "$2"
}
function create_instance {
    # create_instance instance-name zone-name ip-name
    gcloud compute --project "$PROJECT" instances create $1 --project chrome-infra-mon-proxy --machine-type f1-micro --zone $2 --image ubuntu-14-04 --network default --can-ip-forward --tags nat --address $3 --metadata-from-file startup-script=nat_startup.sh
}

function create_nat_route {
    # create_nat_route route-name tag instance-name instance-zone
    echo "Creating new route to hijack traffic from VM tag $2"
    gcloud compute --project "$PROJECT" routes create "$1" --network default --destination-range 0.0.0.0/0 --next-hop-instance "$3" --next-hop-instance-zone "$4" --tags "$2" --priority 800
}

function delete_nat_backend {
    # Deletes NAT routes.
    gcloud compute --project "$PROJECT" routes delete managed-vm1-nat-route
    gcloud compute --project "$PROJECT" routes delete managed-vm2-nat-route
    gcloud compute --project "$PROJECT" routes delete managed-vm3-nat-route
}

function create_nat_backend {
    create_nat_route managed-vm1-nat-route "$GAE_VM1_TAG" nat-box1 "$REGION-a"
    create_nat_route managed-vm2-nat-route "$GAE_VM2_TAG" nat-box2 "$REGION-b"
    create_nat_route managed-vm3-nat-route "$GAE_VM3_TAG" nat-box3 "$REGION-f"
}

# Load balancer over NAT boxes. It only needs to be created once in a
# lifetime of a project.
if false; then
    delete_nat_backend
    create_nat_backend
fi

# Respin the NAT box VMs. Controlled individually, in case only some
# of them have problems.
if false; then
    delete_instance nat-box1 "$REGION-a"
    create_instance nat-box1 "$REGION-a" proxy1
fi

if true; then
    delete_instance nat-box2 "$REGION-b"
    create_instance nat-box2 "$REGION-b" proxy2
fi

if true; then
    delete_instance nat-box3 "$REGION-f"
    create_instance nat-box3 "$REGION-f" proxy3
fi
