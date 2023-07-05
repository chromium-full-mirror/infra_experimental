Running pre-built LUCI sidecar locally
--------------------------------------

(Using podman, but docker should look roughly identical).

```
podman run --rm -it --name luci-sidecar -u 0 \
  --volume ~/.config/chrome_infra/auth:/var/token-cache \
  -p 127.0.0.1:8800:8800 -p 127.0.0.1:8801:8801 -p 127.0.0.1:8900:8900 \
  gcr.io/chops-public-images-prod/luci/utils/sidecar:ci-2023.06.30-57951-8e1c1be \
  -token-cache-dir /var/token-cache \
  -http-addr :8800 \
  -grpc-addr :8801 \
  -admin-addr :8900 \
  -auth-service-host chrome-infra-auth-dev.appspot.com \
  -sidecar-subscribe-to-permission buildbucket.builds.get
```

1. Need to run as root (`-u 0`) inside the container to be able to read the
mounted token cache. This is the simplest way when using Podman on OSX, where
it runs containers in a VM. I suspect on Linux it would be possible to run as
the same uid as the host (`-u $(id -u)`) to allow the container to read the
mounted token cache.
2. Mount host's token cache directory (maintained by `luci-auth`). This is
needed to allow the container to fetch AuthDB.
3. Expose container ports on the host's localhost interface.
4. Actually launch the server, pointing it to use mounted token cache for auth.
5. All LUCI permissions checked by the server needs to be registered via CLI
flags here.


Running the example locally
---------------------------

```
# Launch LUCI sidecar container as instructed above.

# Fetch python dependencies.
./venv.sh
# Run gunicorn server.
./run.sh

# Make a bunch of authenticated requests in a separate terminal.
unset TEST_TARGET_ADDR
./call.sh
```


Running the example on Cloud Run
--------------------------------

Prepare Cloud environment:

1. Create a service account the Cloud Run service will run as.
2. Add this account to dev [auth-trusted-services] group to allow it to access
AuthDB.
3. Add *yourself* as "Service Account User" of this account to allow creating
Cloud Run services that run as this account.
4. If not already an admin, add *yourself* as "Cloud Run Invoker" to be able
to call Cloud Run service to test it.


```
# Substitute with your target GCP project and service account.
export CLOUD_RUN_PROJECT=vadimsh-playground
export CLOUD_RUN_SA=vadimsh-playground@appspot.gserviceaccount.com

# Activate infra.git environment to get `cloudbuildhelper` in PATH.
# See https://chromium.googlesource.com/infra/infra/+/refs/heads/main/go/README.md
# If don't want to use `cloudbuildhelper`, build an image out of Dockerfile in
# any other way and see deploy.sh.
eval `~/infra-superproject/infra/go/env.py`
cloudbuildhelper version

# This builds the image and deploys it to Cloud Run alongside LUCI sidecar.
./deploy.sh

# Hit remote endpoints to verify it works. Substitute with Cloud Run URL
# produced in the previous step.
export TEST_TARGET_ADDR=https://sidecar-helloworld-aykctnts6a-uw.a.run.app
./call.sh
```

[auth-trusted-services]: https://chrome-infra-auth-dev.appspot.com/auth/groups/auth-trusted-services
