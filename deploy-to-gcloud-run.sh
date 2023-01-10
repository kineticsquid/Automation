#!/bin/bash

echo 'Be sure to "gcloud auth login" first'

export DATE=`date '+%F_%H:%M:%S'`

# Run this to create or re-deploy the function
gcloud run deploy automation --allow-unauthenticated --project cloud-run-stuff --region us-central1 \
  --source ./ --set-env-vars=DATE=$DATE \
  --set-env-vars=TWILIO_ACCOUNT_SID=$TWILIO_ACCOUNT_SID \
  --set-env-vars=TWILIO_AUTH_TOKEN=$TWILIO_AUTH_TOKEN \
  --set-env-vars=REDIS_HOST=$REDIS_HOST \
  --set-env-vars=REDIS_PORT=$REDIS_PORT \
  --set-env-vars=REDIS_PW=$REDIS_PW \
  --set-env-vars=BROWSER=$BROWSER \
  --set-env-vars=RWC_ID=$RWC_ID \
  --set-env-vars=RWC_PW=$RWC_PW \
  --set-env-vars=RWC_TIX_ID=$RWC_TIX_ID \
  --set-env-vars=RWC_TIX_PW=$RWC_TIX_PW \
  --set-env-vars=HEADLESS=$HEADLESS \
  --set-env-vars=CONTAINER=$CONTAINER