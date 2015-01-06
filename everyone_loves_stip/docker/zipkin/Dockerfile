FROM dockerfile/java:oracle-java8

MAINTAINER stip

# Install the relevant packages
RUN apt-get update && apt-get install -y python python-dev python-distribute python-pip

RUN git clone http://git-wip-us.apache.org/repos/asf/cassandra.git /home/cassandra
RUN git clone https://github.com/twitter/zipkin.git /home/zipkin
RUN cd /home/zipkin && bin/sbt compile
RUN apt-get install -y ant
rUN cd /home/cassandra && ant

RUN git clone https://github.com/racker/restkin /home/restkin
RUN pip install tryfer requests

# Add our startup script to the container. This script should be executed upon starting the container.
ADD startup.sh /var/www/startup.sh
ADD process.py /var/www/process.py
ADD run_script.sh /var/www/run_script.sh

# Execute the containers startup script which will start many processes/services
CMD ["/bin/bash", "/var/www/startup.sh"]

EXPOSE 8080
