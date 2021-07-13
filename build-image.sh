#!/bin/bash
echo "Tagging and pushing docker image. Be sure to start docker.app first"
echo "To examine contents: 'docker run -it kineticsquid/automation:latest sh'"

docker rmi kineticsquid/automation:latest
docker build --rm --no-cache --pull -t kineticsquid/automation:latest .
docker push kineticsquid/automation:latest

# list the current images
echo "Docker Images..."
docker images
