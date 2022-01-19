#!/bin/bash
echo "Tagging and pushing docker image. Be sure to start docker.app first"
echo "To examine contents: 'docker run -it {image} sh'"

docker rmi kineticsquid/automation-base:latest
docker build --rm --no-cache --pull -t kineticsquid/automatio-base:latest -f Dockerfile-base .
docker push kineticsquid/automation-base:latest

# list the current images
echo "Docker Images..."
docker images
