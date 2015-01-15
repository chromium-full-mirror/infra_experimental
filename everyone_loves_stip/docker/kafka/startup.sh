#!/bin/bash
set -e

/var/www/generate_kafka_cfg.py /home/kafka/server.properties
cd /home/kafka
bin/kafka-server-start.sh server.properties
