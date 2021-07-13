#!/bin/bash

ic target -r us-south
ic target -g default

# Deploy cloud function that will invoke automation
#ic fn namespace target utils
#ic fn action update Fire_Automation ./cloud_function.py --kind python:3.7 --memory 256 --timeout 480000

# Deploy Code Engine image for automation
ic ce proj select -n Utils

REV=$(date +"%y-%m-%d-%H-%M-%S")
echo ${REV}

ic ce app update -n automation -i docker.io/kineticsquid/automation:latest --env TWILIO_ACCOUNT_SID=${TWILIO_ACCOUNT_SID} --env TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN} --env WEBTRAC_USERID=${WEBTRAC_USERID} --env WEBTRAC_PASSWORD=${WEBTRAC_PASSWORD} --env HEADLESS=${HEADLESS} --env BROWSER=${BROWSER} --env PYDEVD_USE_CYTHON=${PYDEVD_USE_CYTHON} --env REDIS_HOST=${REDIS_HOST} --env REDIS_PORT=${REDIS_PORT} --env REDIS_PW=${REDIS_PW} --rn ${REV} --min 1

ic ce rev list --app automation
ic ce app events --app automation
ic ce app logs --app automation