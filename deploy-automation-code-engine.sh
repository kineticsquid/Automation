#!/bin/bash

ibmcloud target -r us-south
ibmcloud target -g default

# Deploy cloud function that will invoke automation
#ic fn namespace target utils
#ic fn action update Fire_Automation ./cloud_function.py --kind python:3.7 --memory 256 --timeout 480000

# Deploy Code Engine image for automation
ibmcloud ce proj select -n Utils

REV=$(date +"%y-%m-%d-%H-%M-%S")
echo ${REV}

ibmcloud ce app update -n automation -i docker.io/kineticsquid/automation:latest --env TWILIO_ACCOUNT_SID=${TWILIO_ACCOUNT_SID} --env TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN} --env WEBTRAC_USERID=${WEBTRAC_USERID} --env WEBTRAC_PASSWORD=${WEBTRAC_PASSWORD} --env HEADLESS=${HEADLESS} --env BROWSER=${BROWSER} --env PYDEVD_USE_CYTHON=${PYDEVD_USE_CYTHON} --env REDIS_HOST=${REDIS_HOST} --env REDIS_PORT=${REDIS_PORT} --env REDIS_PW=${REDIS_PW} --rn ${REV} --min 1 --memory 8G

ibmcloud ce rev list --app automation
ibmcloud ce app events --app automation
ibmcloud ce app logs --app automation