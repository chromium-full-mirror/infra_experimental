#!/bin/bash
set -e

cd /home/cassandra
bin/cassandra
sleep 2
cd /home/zipkin
/home/cassandra/bin/cqlsh -f /var/www/schema.cql
bin/web &
bin/collector cassandra &
bin/query cassandra &

cd /home/restkin
./bin/restkin-api --scribe tcp:localhost:9410 &

sleep 60
bash /var/www/run_script.sh
