#!/bin/bash
set -e

cd /home/kafka
bin/kafka-server-start.sh config/server.properties
