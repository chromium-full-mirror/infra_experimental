#!/bin/bash

DOCKER_LOG='docker_build.log'
PROJECT=chrome-infra-mon-proxy-dev

rm -f $DOCKER_LOG

if docker build . | tee -a $DOCKER_LOG; then
  image_hash=`grep 'Successfully built' $DOCKER_LOG | awk '{print $3;}'`
  image_tag=gcr.io/`echo $PROJECT | tr - _`/monitoring_proxy_go_$image_hash
  docker tag $image_hash $image_tag
  gcloud --project $PROJECT docker push $image_tag
  echo
  echo Done. Update manifest with new image tag:
  echo $image_tag
else
  echo 'ERROR: docker build failed.'
fi
