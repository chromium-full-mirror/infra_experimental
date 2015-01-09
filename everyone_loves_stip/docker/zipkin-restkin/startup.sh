#!/bin/bash
set -e

cd /home/cassandra
bin/cassandra
sleep 10
n=0
until [ $n -ge 5 ]
do
  /home/cassandra/bin/cqlsh -f /var/www/schema.cql && break
  n=$[$n+1]
  sleep 15
done
cd /home/zipkin
bin/collector cassandra &
bin/query cassandra &
bin/web &

cd /home/restkin
./bin/restkin-api --scribe tcp:localhost:9410
