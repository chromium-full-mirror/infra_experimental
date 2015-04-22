# Create the base image using Dockerfile_base, update the image tag
# below accordingly. Then:

#   cd <directory of this Dockerfile>
#   docker build .    # Note the resulting image-hash.
#   docker tag <image-hash> \
#       gcr.io/chrome_infra_loadtest/loadtest_<image-hash>
#   gcloud --project chrome-infra-loadtest preview docker push <new image tag>

### To make the image available locally:
# gcloud --project chrome-infra-loadtest preview docker pull <image tag>


FROM gcr.io/chrome_infra_loadtest/base_loadtest_45c63a3ce4ce

ADD . /

CMD python /loadtest.py
