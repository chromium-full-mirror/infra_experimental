FROM dockerfile/java:oracle-java8

MAINTAINER stip

# Install the relevant packages
RUN apt-get update && apt-get install -y python python-dev python-distribute python-pip ant

RUN git clone http://git-wip-us.apache.org/repos/asf/cassandra.git /home/cassandra
RUN git clone https://github.com/twitter/zipkin.git /home/zipkin
RUN git clone https://github.com/racker/restkin /home/restkin

RUN cd /home/zipkin && bin/sbt compile
rUN cd /home/cassandra && ant

RUN pip install tryfer

# Add our startup script to the container. This script should be executed upon starting the container.
ADD startup.sh /var/www/startup.sh
ADD schema.cql /var/www/schema.cql

# Execute the containers startup script which will start many processes/services
CMD ["/bin/bash", "/var/www/startup.sh"]

EXPOSE 6956
EXPOSE 8080
EXPOSE 9160
