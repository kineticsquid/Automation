#!/bin/bash

echo "http://0.0.0.0:5005/"

# Now run locally. Use "rm" to remove the container once it finishes
docker run --rm -p 5005:5030 --env USERID=${USERID} --env PASSWORD=${PASSWORD} --env TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN} --env TWILIO_ACCOUNT_SID=${TWILIO_ACCOUNT_SID} kineticsquid/appen:latest



