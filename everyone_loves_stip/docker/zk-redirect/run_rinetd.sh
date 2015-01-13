#!/bin/bash
set -e

/var/www/write_rinetd_conf.py /etc/rinetd.conf
sudo /etc/init.d/rinetd restart

# run a foreground process forever
tail -f /dev/null
