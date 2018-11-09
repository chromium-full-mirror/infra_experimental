FROM node:8-stretch

RUN apt-get update \
    && apt-get install -y python python-dev python-pip \
    && apt-get clean && rm -rf /var/cache/apt/* && rm -rf /var/lib/apt/lists/* && rm -rf /tmp/*

RUN pip install \
    python-language-server \
    flake8 \
    autopep8

ARG version=latest

# Install depot_tools.
RUN git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git /home/depot_tools
ENV PATH="/home/depot_tools:${PATH}"

# Install the infra directory

WORKDIR /home/theia
ADD $version.package.json ./package.json
ARG GITHUB_TOKEN
RUN yarn --cache-folder ./ycache && rm -rf ./ycache
RUN yarn theia build
EXPOSE 3000
ENV SHELL /bin/bash
ENTRYPOINT [ "yarn", "theia", "start", "/home/project", "--hostname=0.0.0.0" ]
