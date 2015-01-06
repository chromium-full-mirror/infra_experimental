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
watch -n 60 python /var/www/process.py
