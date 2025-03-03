#!/bin/bash

# Define the directory and image name
repo_name="$1"
service_name="$2"

# Check service name set
if [ -z "$service_name" ]; then
    echo "ERROR: Service name not provided as command line parameter 2. Repo name is parameter 1"
    exit 1
fi

# Get the current directory name
current_dir="${PWD##*/}"

# Check if the current directory is the service directory
if [ "$current_dir" == "$service_name" ]; then
    cd ..
fi

if [ -f "$service_name/Dockerfile" ]; then
    echo "Building using Dockerfile specific to $service_name"
    docker build -t "$service_name" . -f "$service_name/Dockerfile"
else
    echo "Building using common Dockerfile"
    docker build -t "$service_name" . -f common/Dockerfile --build-arg SERVICE_NAME="$service_name"
fi

docker tag "$service_name" "$repo_name/$service_name"
docker push "$repo_name/$service_name"
