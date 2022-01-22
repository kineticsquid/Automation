#!/bin/bash

docker pull kineticsquid/automation:latest

docker run --rm -p 5030:5030 \
  --env TWILIO_ACCOUNT_SID=${TWILIO_ACCOUNT_SID} \
  --env TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN} \
  --env REDIS_HOST=${REDIS_HOST} \
  --env REDIS_PW=${REDIS_PW} \
  --env REDIS_PORT=${REDIS_PORT} \
  --env WEBTRAC_USERID=${WEBTRAC_USERID} \
  --env WEBTRAC_PASSWORD=${WEBTRAC_PASSWORD} \
  --env PORT=${PORT} \
  kineticsquid/automation:latest



