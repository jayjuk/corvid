#!/bin/bash

# Check for .env file in ../common
if [ -f "../common/.env" ]; then
    env_file_path="../common/.env"
elif [ -f "./common/.env" ]; then
    env_file_path="./common/.env"
else
    echo ".env file not found in ../common or ./common."
    exit 1
fi

echo "Running Image Server..."
docker rm gameclient_local
docker run --name gameclient_local -p 3000:3000 jayjuk/gameclient
