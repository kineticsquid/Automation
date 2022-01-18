#!/bin/bash
echo "Tagging and pushing docker image. Be sure to start docker.app first"
echo "To examine contents: 'docker run -it {image} sh'"

docker rmi kineticsquid/automation-gcloud:latest
docker build --rm --no-cache --pull -t kineticsquid/automation-gcloud:latest -f Dockerfile .
docker push kineticsquid/automation-gcloud:latest

# list the current images
echo "Docker Images..."
docker images




