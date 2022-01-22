#!/bin/bash

docker pull kineticsquid/automation-ff:latest
docker run --rm \
  --env WEBTRAC_USERID=${WEBTRAC_USERID} \
  --env WEBTRAC_PASSWORD=${WEBTRAC_PASSWORD} \
  kineticsquid/automation-ff:latest



