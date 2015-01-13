#!/bin/bash
set -e

cd /var/www
python hostname_writer.py
cd /var/www/hostname
python -m SimpleHTTPServer 9999 &

/var/www/generate_zoo_cfg.py /home/zookeeper/zoo.cfg
cd /home/zookeeper
bin/zkServer.sh --config . start-foreground
