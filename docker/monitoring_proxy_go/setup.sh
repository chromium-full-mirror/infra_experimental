#!/bin/bash

PROJECT="chrome-infra-mon-proxy-dev"
REGION="us-central1"
INSTANCE_TYPE="n1-standard-1"

function delete_instance {
    # delete_instance instance-name zone-name
    echo "Deleting $1"
    gcloud compute -q --project "$PROJECT" instances delete "$1" --zone "$2"
}
function create_instance {
    # create_instance instance-name zone-name ip-name
    # NOTE: ip-name is currently unused. Add --address $3 in production version.
    echo "Creating $1"
    gcloud compute -q --project "$PROJECT" instances create $1 --project "$PROJECT" --machine-type $INSTANCE_TYPE --zone $2 --image container-vm --network default --metadata-from-file google-container-manifest=monitoring_proxy_go_containers.yaml
}

function respin_proxy1 {
    delete_instance proxy-go1 "$REGION-a"
    create_instance proxy-go1 "$REGION-a" proxy1
}

function respin_proxy2 {
    delete_instance proxy-go2 "$REGION-b"
    create_instance proxy-go2 "$REGION-b" proxy2
}

function respin_proxy3 {
    delete_instance proxy-go3 "$REGION-c"
    create_instance proxy-go3 "$REGION-c" proxy3
}

case $1 in
    proxy1)
	respin_proxy1
	;;
    proxy2)
	respin_proxy2
	;;
    proxy3)
	respin_proxy3
	;;
    *)
	echo "Unknown command: $1. Use proxy[1-3]."
        ;;
esac
