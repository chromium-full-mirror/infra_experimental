FROM dockerfile/ubuntu:14.04

MAINTAINER stip

# Install the relevant packages
RUN apt-get update && apt-get install -y python python-dev python-distribute python-pip
RUN pip install requests

# Add our startup script to the container. This script should be executed upon starting the container.
ADD run_script.sh /var/www/run_script.sh
ADD process.py /var/www/process.py

# Execute the containers startup script which will start many processes/services
CMD ["/bin/bash", "/var/www/run_script.sh"]
