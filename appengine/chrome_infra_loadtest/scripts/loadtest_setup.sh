#!/bin/bash
# Run this script from its directory, to correctly pick up loadtest_startup.sh:
# cd scripts
# ./loadtest_setup.sh

PROJECT="chrome-infra-loadtest"
# Use a non-US zone to save the US quota.
REGION="asia-east1"
ZONE_ASIA="asia-east1-b"
ZONE_US="us-central1-f"
ZONE_EU="europe-west1-d"
LOADTEST_INSTANCES_ASIA=15
LOADTEST_INSTANCES_US=20
LOADTEST_INSTANCES_EU=20

function delete_instance {
    # delete_instance zone instance-name
    echo delete instance $2 in zone $1
    gcloud compute -q --project "$PROJECT" instances delete "$2" --zone "$1" &
}

function create_instance {
    # create_instance zone instance_name
    echo create instance $2 in zone $1
    gcloud compute -q --project "$PROJECT" instances create $2 --project "$PROJECT" --machine-type n1-standard-1 --zone "$1" --image container-vm --network default --metadata-from-file google-container-manifest=loadtest_containers.yaml startup-script=loadtest_startup.sh &
}

function delete_instance_asia {
    delete_instance "$ZONE_ASIA" "loadtest-asia$1"
}

function delete_instance_us {
    delete_instance "$ZONE_US" "loadtest-us$1"
}

function delete_instance_eu {
    delete_instance "$ZONE_EU" "loadtest-eu$1"
}

function create_instance_asia {
    create_instance "$ZONE_ASIA" "loadtest-asia$1"
}

function create_instance_us {
    create_instance "$ZONE_US" "loadtest-us$1"
}

function create_instance_eu {
    create_instance "$ZONE_EU" "loadtest-eu$1"
}

function down {
# Destroy load test instances. Make sure you've listed them all.
    if [[ $LOADTEST_INSTANCES_ASIA != 0 ]]; then
	for i in $(seq 1 $LOADTEST_INSTANCES_ASIA); do
	    delete_instance_asia "$i"
	done
    fi
    if [[ $LOADTEST_INSTANCES_US != 0 ]]; then
	for i in $(seq 1 $LOADTEST_INSTANCES_US); do
	    delete_instance_us "$i"
	done
    fi
    if [[ $LOADTEST_INSTANCES_EU != 0 ]]; then
	for i in $(seq 1 $LOADTEST_INSTANCES_EU); do
	    delete_instance_eu "$i"
	done
    fi
}

# Spin up load test instances. Add as many as you need.
function up {
    if [[ $LOADTEST_INSTANCES_ASIA != 0 ]]; then
	for i in $(seq 1 $LOADTEST_INSTANCES_ASIA); do
	    create_instance_asia "$i"
	done
    fi
    if [[ $LOADTEST_INSTANCES_US != 0 ]]; then
	for i in $(seq 1 $LOADTEST_INSTANCES_US); do
	    create_instance_us "$i"
	done
    fi
    if [[ $LOADTEST_INSTANCES_EU != 0 ]]; then
	for i in $(seq 1 $LOADTEST_INSTANCES_EU); do
	    create_instance_eu "$i"
	done
    fi
}

case $1 in
    up)
	up
	;;
    down)
	down
	;;
    *)
	echo "Unknown command: $1. Use up or down."
esac
