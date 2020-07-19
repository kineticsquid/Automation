#!/bin/bash
echo "Tagging and pushing docker image. Be sure to start docker.app first"
echo "Be sure to login at dockerhub first with creds below"
echo "kineticsquid - ${DOCKER_HUB_ACCESS_TOKEN}"
echo "To examine contents: 'docker run -it kineticsquid/appen:latest sh'"

# Use "--rm" to remove intermediate images
docker build --rm -t kineticsquid/appen:latest .
docker push kineticsquid/appen:latest

# list the current images
echo "Docker Images..."
docker images