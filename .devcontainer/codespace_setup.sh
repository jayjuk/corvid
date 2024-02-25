#!/bin/bash

# Stop on error
set -e

echo 'export PYTHONPATH=\"/usr/local/python/current:/workspaces/jaysgame/common"' >> ~/.bashrc

echo $GEMINI_DOT_KEY > gameserver/gemini.key.test

