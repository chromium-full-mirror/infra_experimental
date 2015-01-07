#!/bin/bash
set -e

cd /home/cassandra
bin/cassandra
sleep 10
/home/cassandra/bin/cqlsh -f /var/www/schema.cql
cd /home/zipkin
bin/collector cassandra &
bin/query cassandra &
bin/web &

cd /home/restkin
./bin/restkin-api --scribe tcp:localhost:9410 &

sleep 60
bash /var/www/run_script.sh
