#!/bin/bash

# Stop on error
set -e

echo 'export PYTHONPATH=\"/usr/local/python/current:/workspaces/jaysgame/common"' >> ~/.bashrc
export PYTHONPATH=\"/usr/local/python/current:/workspaces/jaysgame/common

curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

pip install -r ./common/requirements.txt
pip install -r ./gameserver/requirements.txt
pip install -r ./aibroker/requirements.txt
