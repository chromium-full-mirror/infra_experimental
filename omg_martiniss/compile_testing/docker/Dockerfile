FROM ubuntu:xenial

RUN apt-get update
RUN apt-get install -y git byobu vim python lsb lsof sudo netcat rinetd
RUN apt-get update
# install what install build deps would do
RUN apt-get install -y ant apache2-bin autoconf binutils-aarch64-linux-gnu binutils-arm-linux-gnueabihf bison cdbs cmake curl devscripts dpkg-dev elfutils fakeroot flex fonts-ipafont g++ g++-mingw-w64-i686 gawk git-core git-svn gperf intltool lib32gcc1 lib32ncurses5-dev lib32stdc++6 lib32z1-dev libasound2 libasound2-dev libatk1.0-0 libatk1.0-dbg libav-tools libbluetooth-dev libbrlapi-dev libbrlapi0.6 libbz2-1.0 libbz2-dev libc6 libc6-dbg libc6-dev-armhf-cross  libcairo2 libcairo2-dbg libcairo2-dev libcap-dev libcap2 libcups2 libcups2-dev libcurl4-gnutls-dev libdrm-dev libelf-dev libexpat1 libffi-dev libffi6 libffi6-dbg libfontconfig1 libfontconfig1-dbg libfreetype6 libgbm-dev libgl1-mesa-dev libgles2-mesa-dev libglib2.0-0 libglib2.0-0-dbg libglib2.0-dev libglu1-mesa-dev libgnome-keyring-dev libgnome-keyring0 libgtk-3-0 libgtk-3-0-dbg libgtk-3-dev libgtk2.0-0 libgtk2.0-0-dbg libgtk2.0-dev libjpeg-dev libkrb5-dev libnspr4 libnspr4-dbg libnspr4-dev libnss3 libnss3-dbg libnss3-dev libpam0g libpam0g-dev libpango1.0-0 libpango1.0-0-dbg libpci-dev libpci3 libpcre3 libpcre3-dbg libpixman-1-0 libpixman-1-0-dbg libpulse-dev libpulse0 libsctp-dev libspeechd-dev libspeechd2 libsqlite3-0 libsqlite3-0-dbg libsqlite3-dev libssl-dev libstdc++6 libtinfo-dev libtool libudev-dev libudev1 libwww-perl libx11-6 libx11-6-dbg libx11-xcb1 libx11-xcb1-dbg libxau6 libxau6-dbg libxcb1 libxcb1-dbg libxcomposite1 libxcomposite1-dbg libxcursor1 libxcursor1-dbg libxdamage1 libxdamage1-dbg libxdmcp6 libxdmcp6-dbg libxext6 libxext6-dbg libxfixes3 libxfixes3-dbg libxi6 libxi6-dbg libxinerama1 libxinerama1-dbg libxkbcommon-dev libxrandr2 libxrandr2-dbg libxrender1 libxrender1-dbg libxslt1-dev libxss-dev libxt-dev libxtst-dev libxtst6 libxtst6-dbg linux-libc-dev-armhf-cross locales mesa-common-dev openbox patch perl pkg-config python python-cherrypy3 python-crypto python-dev python-numpy python-opencv python-openssl python-psutil python-yaml realpath rpm ruby subversion texinfo wdiff x11-utils xcompmgr xsltproc xutils-dev xvfb zip zlib1g zlib1g-dbg
# enables us to install these fonts later in install-build-deps.sh
RUN echo ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true | debconf-set-selections

# Setup new user; we appear to need this user to run goma.
RUN useradd compile

RUN echo "root:docker" | chpasswd
RUN echo "compile:docker" | chpasswd
RUN echo "compile ALL=(ALL) ALL" > /etc/sudoers

RUN mkdir /home/compile
RUN chown -R compile /home/compile

# Set up environment variables
USER compile
# Get depot tools
ENV HOME /home/compile
RUN git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git $HOME/depot_tools
ENV PATH=$PATH:$HOME/depot_tools

# Fetch chromium
RUN mkdir -p $HOME/chromium
WORKDIR $HOME/chromium

RUN fetch --no-history --nohooks android
WORKDIR $HOME/chromium/src
# Makes us pretend to be a bot so we don't have to accept a license
ENV CHROME_HEADLESS 1
RUN gclient runhooks

USER root
# copy some scripts to compile home dir
COPY goma_fetched /goma
RUN chown -R compile /goma
RUN chown compile /home/compile
COPY goma_oauth /home/compile/.goma_oauth
RUN chown -R compile /home/compile/.goma_oauth

RUN echo "root ALL=(ALL) ALL" > /etc/sudoers
RUN DEBIAN_FRONTEND=text /home/compile/chromium/src/build/install-build-deps-android.sh --no-prompt
USER compile

ENV USER compile
ENV GOMA_OAUTH2_CONFIG_FILE=/home/compile/.goma_oauth

ARG MASTER=tryserver.chromium.linux
ARG BUILDER=linux_chromium_rel_ng
RUN python /home/compile/chromium/src/tools/mb/mb.py gen -m $MASTER -b $BUILDER --config-file /home/compile/chromium/src/tools/mb/mb_config.pyl --goma-dir /goma/goma //out/Default

USER root
WORKDIR /home/compile
COPY compile.py /home/compile/compile.py
RUN chown -R compile /home/compile/compile.py
USER compile
WORKDIR $HOME/chromium/src

ENTRYPOINT ["/usr/bin/python", "/home/compile/compile.py"]
CMD ["unittests"]

EXPOSE 8080

