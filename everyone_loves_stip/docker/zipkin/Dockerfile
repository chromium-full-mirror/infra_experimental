FROM dockerfile/java:oracle-java8

MAINTAINER stip

# Install the relevant packages
RUN apt-get update && apt-get install -y python python-dev python-distribute python-pip
#RUN pip install numpy

RUN git clone https://github.com/twitter/zipkin.git /home/zipkin
RUN cd /home/zipkin && bin/sbt compile

# Add our startup script to the container. This script should be executed upon starting the container.
ADD startup.sh /var/www/startup.sh

#ADD crbug_stats.py /var/www/crbug_stats.py
#ADD query_config.json /var/www/query_config.json
#ADD upload.py /var/www/upload.py
#ADD .auth_token /var/www/.auth_token

# Execute the containers startup script which will start many processes/services
CMD ["/bin/bash", "/var/www/startup.sh"]

EXPOSE 8080
