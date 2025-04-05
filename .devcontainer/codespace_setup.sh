#!/bin/bash

# Stop on error
set -e

echo 'export PYTHONPATH=\"/usr/local/python/current:/workspaces/corvid/common"' >> ~/.bashrc
export PYTHONPATH=\"/usr/local/python/current:/workspaces/corvid/common

curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

pip install -r ./common/requirements.txt
pip install -r ./orchestrator/requirements.txt
pip install -r ./aibroker/requirements.txt
