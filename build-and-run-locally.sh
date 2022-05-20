#!/bin/bash
echo "Tagging and pushing docker image. Be sure to start docker.app first"
echo "To examine contents: 'docker run -it {image} sh'"

docker rmi kineticsquid/automation:latest
docker build --rm --no-cache --pull -t kineticsquid/automation:latest -f Dockerfile .
docker push kineticsquid/automation:latest

# list the current images
echo "Docker Images..."
docker images

echo "Now running..."
./.vscode/run-image-locally.sh