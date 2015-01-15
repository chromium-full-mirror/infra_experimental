FROM dockerfile/java:oracle-java8

MAINTAINER stip

# Install the relevant packages
RUN apt-get update && apt-get install -y python python-dev python-distribute python-pip

RUN git clone https://github.com/apache/kafka.git /home/kafka

RUN cd /home/kafka && bin/sbt compile

# Add our startup script to the container. This script should be executed upon starting the container.
ADD startup.sh /var/www/startup.sh

# Execute the containers startup script which will start many processes/services
CMD ["/bin/bash", "/var/www/startup.sh"]

