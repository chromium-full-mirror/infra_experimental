#!/bin/bash

cd /home/cassandra
bin/cassandra
cd /home/zipkin
bin/web &
bin/collector cassandra &
bin/query cassandra &

cd /home/restkin
./bin/restkin-api --scribe tcp:localhost:9410 &

sleep 20
while true;
do python /var/www/process.py;
sleep 60;
done
