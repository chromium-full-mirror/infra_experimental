#!/bin/bash
python -c "import requests; exec requests.get('https://$SWARMING_HOSTNAME/bootstrap').text"
