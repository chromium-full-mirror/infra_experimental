FROM ubuntu:14.04

MAINTAINER stip

# Install the relevant packages
RUN apt-get update && apt-get install -y python python-dev python-distribute python-pip rinetd
RUN pip install jinja2

# Add our startup script to the container. This script should be executed upon starting the container.
ADD run_rinetd.sh /var/www/run_rinetd.sh
ADD rinetd_cfg.template /var/www/rinetd_cfg.template
ADD write_rinetd_conf.py /var/www/write_rinetd_conf.py

# Execute the containers startup script which will start many processes/services
CMD ["/bin/bash", "/var/www/run_rinetd.sh"]
