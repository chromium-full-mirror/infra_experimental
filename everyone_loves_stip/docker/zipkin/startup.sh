#!/bin/bash
set -e

cd /home/cassandra
bin/cassandra
sleep 2
cd /home/zipkin
/home/cassandra/bin/cassandra-cli -host localhost -port 9160 -f zipkin-cassandra/src/schema/cassandra-schema.txt
bin/web &
bin/collector cassandra &
bin/query cassandra &

cd /home/restkin
./bin/restkin-api --scribe tcp:localhost:9410 &

sleep 60
bash /var/www/run_script.sh
