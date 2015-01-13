FROM dockerfile/java:oracle-java8

MAINTAINER stip

# Install the relevant packages
RUN apt-get update && apt-get install -y python python-dev python-distribute python-pip ant rinetd
RUN git clone --branch release-3.5.0 https://github.com/apache/zookeeper /home/zookeeper
RUN cd /home/zookeeper && ant
RUN pip install jinja2

# Add our startup script to the container. This script should be executed upon starting the container.
ADD startup.sh /var/www/startup.sh
ADD hostname_writer.py /var/www/hostname_writer.py
ADD generate_zoo_cfg.py /var/www/generate_zoo_cfg.py
ADD zoo_cfg.template /var/www/zoo_cfg.template
ADD log4j.properties /home/zookeeper/log4j.properties
ADD rinetd_cfg.template /var/www/rinetd_cfg.template
ADD write_rinetd_conf.py /var/www/write_rinetd_conf.py

# Execute the containers startup script which will start many processes/services
CMD ["/bin/bash", "/var/www/startup.sh"]

EXPOSE 2181
EXPOSE 2888
EXPOSE 3888
EXPOSE 2182
EXPOSE 2889
EXPOSE 3889
