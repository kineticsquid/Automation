#!/bin/bash
echo "Tagging and pushing docker image. Be sure to start docker.app first"
echo "Be sure to login at dockerhub first with creds below"
echo "kineticsquid - ${DOCKER_HUB_ACCESS_TOKEN}"
echo "To examine contents: 'docker run -it kineticsquid/automation:latest sh'"

ibmcloud cr login
docker rmi kineticsquid/automation:latest
# Use "--rm" to remove intermediate images
docker build --rm --no-cache --pull -t kineticsquid/automation:latest -f Dockerfile-Safari .
docker push kineticsquid/automation:latest

# list the current images
echo "Docker Images..."
docker images

echo "IBM Cloud CR Images..."
ibmcloud cr images