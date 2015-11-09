FROM ubuntu:14.04

MAINTAINER stip

# Install the relevant packages
RUN apt-get update && apt-get install -y python python-dev python-distribute python-pip libusb-1.0-0 usbutils swig libssl-dev curl
RUN pip install requests m2crypto

VOLUME /b

RUN useradd chrome-bot -mU
RUN usermod -g plugdev chrome-bot

# Add our startup script to the container. This script should be executed upon starting the container.
ADD run_script.sh /home/chrome-bot/run_script.sh
RUN chown chrome-bot /home/chrome-bot/run_script.sh

USER chrome-bot
WORKDIR /home/chrome-bot


# Execute the containers startup script which will start many processes/services
CMD ["/bin/bash", "/home/chrome-bot/run_script.sh"]
