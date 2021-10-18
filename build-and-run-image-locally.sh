#!/bin/bash
echo "Tagging and pushing docker image. Be sure to start docker.app first"
echo "To examine contents: 'docker run -it {image} sh'"

docker rmi kineticsquid/automation-gcloud:latest
docker build --rm --no-cache --pull -t kineticsquid/automation-gcloud:latest -f Dockerfile .
docker push kineticsquid/automation-gcloud:latest

# list the current images
echo "Docker Images..."
docker images

# Run
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
  --env CONTAINER=${CONTAINER} \
  --env HEADLESS=${HEADLESS} \
  kineticsquid/automation-gcloud:latest




