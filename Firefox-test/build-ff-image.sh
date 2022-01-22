#!/bin/bash
echo "Tagging and pushing docker image. Be sure to start docker.app first"
echo "To examine contents: 'docker run -it {image} sh'"

docker rmi kineticsquid/automation-ff:latest
docker build --rm --no-cache --pull -t kineticsquid/automation-ff:latest -f ./Firefox-test/Dockerfile-ff .
docker push kineticsquid/automation-ff:latest

# list the current images
echo "Docker Images..."
docker images
