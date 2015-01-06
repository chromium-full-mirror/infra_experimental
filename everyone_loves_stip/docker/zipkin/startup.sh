#!/bin/bash

cd /home/cassandra
bin/cassandra
cd /home/zipkin
bin/web &
bin/collector cassandra &
bin/query cassandra &

cd /home/restkin
./bin/restkin-api --scribe tcp:localhost:9410 &

python /var/www/process.py 834173002
watch -n 10 echo "hello"
