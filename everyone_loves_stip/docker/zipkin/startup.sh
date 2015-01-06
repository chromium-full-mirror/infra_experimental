#!/bin/bash

cd /home/cassandra
bin/cassandra
cd /home/zipkin
/home/cassandra/bin/cassandra-cli -host localhost -port 9160 -f zipkin-cassandra/src/schema/cassandra-schema.txt
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
