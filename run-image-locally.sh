#!/bin/bash

echo "http://192.168.1.102:5030/"

# Now run locally. Use "rm" to remove the container once it finishes
docker run --rm -p 5030:5030 --env APPEN_USERID=${APPEN_USERID} --env APPEN_PASSWORD=${APPEN_PASSWORD} --env WEBTRAC_USERID=${WEBTRAC_USERID} --env WEBTRAC_PASSWORD=${WEBTRAC_PASSWORD} --env TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN} --env TWILIO_ACCOUNT_SID=${TWILIO_ACCOUNT_SID} --env REDIS_HOST=${REDIS_HOST} --env REDIS_PORT=${REDIS_PORT} --env REDIS_PW=${REDIS_PW} --env BROWSER=${BROWSER} --env HEADLESS=${HEADLESS} kineticsquid/automation:latest



