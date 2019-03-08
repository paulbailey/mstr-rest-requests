#!/usr/bin/env bash

npm install serverless -g
mkdir -p build/python/
pip install --target build/python/ mstr-rest-requests
serverless deploy