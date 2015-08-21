#!/bin/bash
curl -sSLOJ https://$SWARMING_HOSTNAME/bot_code
python swarming_bot.zip start_bot
