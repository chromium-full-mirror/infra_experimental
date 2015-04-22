#!/bin/bash
echo "# crontab for user `whoami`" > crontab
crontab -l >> crontab
echo "* * * * * /bin/bash -c \"sudo docker run --rm gcr.io/chrome_infra_loadtest/loadtest_4ba79dda8955\"" >> crontab
crontab crontab
