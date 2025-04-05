#!/bin/bash

# Update the package index
sudo apt update

# Install the required packages
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Add the Docker repository
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

# Add the Docker repository to the APT sources
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"

# Update the package index again
sudo apt update

# Install Docker
sudo apt install -y docker-ce

# Start the Docker service
sudo systemctl start docker

# Enable the Docker service to start automatically
sudo systemctl enable docker

# Add the current user to the Docker group
sudo usermod -aG docker $USER

echo "Docker installation complete. Please log out and log back in to run Docker without sudo."