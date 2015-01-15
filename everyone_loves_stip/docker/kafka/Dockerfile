FROM dockerfile/java:oracle-java8

MAINTAINER stip

# Install the relevant packages
RUN apt-get update && apt-get install -y python python-dev python-distribute python-pip

RUN git clone https://github.com/apache/kafka.git /home/kafka
RUN wget https://services.gradle.org/distributions/gradle-2.2.1-all.zip -O /tmp/gradle-2.2.1-all.zip
RUN unzip /tmp/gradle-2.2.1-all.zip -d /home/gradle
ENV PATH /home/gradle/gradle-2.2.1/bin:$PATH

RUN cd /home/kafka && gradle wrapper
RUN cd /home/kafka && ./gradlew jar

RUN pip install jinja2

# Add our startup script to the container. This script should be executed upon starting the container.
ADD startup.sh /var/www/startup.sh
ADD generate_kafka_cfg.py /var/www/generate_kafka_cfg.py
ADD kafka_server_config.properties.template /var/www/kafka_server_config.properties.template

# Execute the containers startup script which will start many processes/services
CMD ["/bin/bash", "/var/www/startup.sh"]

