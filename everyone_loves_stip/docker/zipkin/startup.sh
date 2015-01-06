#!/bin/bash

cd /home/cassandra
bin/cassandra
cd /home/zipkin
bin/web &
bin/collector cassandra &
bin/query cassandra &
