This version of the proxy is a proof of concept, and is designed to
work with chrome-infra-loadtest.appspot.com.

The clients would push directly to PubSub using patched ts_mon
library, and a thin Go client running on a GCE VM with a static
(whitelisted) IP will poll the subscription and forward data to the
final endpoint.

Build the container:
--------------------

 `cd go
  ./install-deps.sh # Need to run only once, to init .verdor dir.
  source env.sh     # Will go away once moved to infra(_internal).

  go build src/infra_experimental/services/monitoring_proxy
  cp monitoring_proxy ../docker/monitoring_proxy_go
  cd ../docker/monitoring_proxy_go
  cp <credentials for final endpoint> loadtest_creds.json
  cp <credentials for PubSub project> pubsub_creds.json

  docker build .  # Note the resulting image hash.`

Push the container image to Google Container Repository:
--------------------------------------------------------

 `docker tag <image-hash> \
      gcr.io/chrome_infra_mon_proxy/monitoring_proxy_go_<image-hash>
  gcloud --project chrome-infra-mon-proxy docker push \
      gcr.io/chrome_infra_mon_proxy/monitoring_proxy_go_<image-hash>`

Deploy the new container, or revert the previously deployed change:
-------------------------------------------------------------------

  * Update the image hash in monitoring_proxy_go_containers.yaml
  * `./setup.sh proxy1 # This will respin the VM with the new container.`

To Do
-----

 * Make monitoring_proxy.sh read the credentials from the metadata server on GCE,
   write to a file and give it to the executable.
