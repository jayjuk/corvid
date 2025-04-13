#!/bin/bash

# Check for .env file in ../common
if [ -f "../common/.env" ]; then
    env_file_path="../common/.env"
elif [ -f "./common/.env" ]; then
    # Check for .env file in ./common
    env_file_path="./common/.env"
else
    echo ".env file not found in ../common or ./common."
    exit 1
fi

# Load the environment variables from the .env file
echo "Loading env variables from common .env file in local execution..."
while IFS='=' read -r key value; do
    # Skip lines that start with #
    if [[ $key == \#* ]]; then
        continue
    fi
    export "TF_VAR_$key=$value"
done < "$env_file_path"

# Check if the first parameter is "docker" (case insensitive)
if [ "$(echo "$1" | tr '[:upper:]' '[:lower:]')" != "docker" ]; then
    cd droplet_configuration
    terraform plan -out=infra.out
    terraform apply "infra.out"
    cd ..
fi

# Set some variables
export TF_VAR_AI_COUNT=1
export TF_VAR_MODEL_SYSTEM_MESSAGE=""

# Execute Terraform
cd docker_configuration
terraform plan -out=infra.out
terraform apply "infra.out"
cd ..