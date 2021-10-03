#!/bin/bash

# Now run locally. Use "rm" to remove the container once it finishes
#docker run --rm kineticsquid/automation-gcloud:latest \
#  --env PORT=${PORT}

export DATE=`date '+%F_%H:%M:%S'`

docker run --rm -p 5030:5030 \
  --env TWILIO_ACCOUNT_SID=${TWILIO_ACCOUNT_SID} \
  --env TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN} \
  --env REDIS_HOST=${REDIS_HOST} \
  --env REDIS_PW=${REDIS_PW} \
  --env REDIS_PORT=${REDIS_PORT} \
  --env BROWSER=${BROWSER} \
  --env WEBTRAC_USERID=${WEBTRAC_USERID} \
  --env WEBTRAC_PASSWORD=${WEBTRAC_PASSWORD} \
  --env PORT=${PORT} \
  --env DATE=$DATE \
  kineticsquid/automation-gcloud:latest



