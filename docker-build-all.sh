#!/bin/bash

set -o errexit

docker build -t nta.utils:latest nta.utils
docker build -t htmengine:latest htmengine
docker build -t taurus.metric_collectors:latest taurus.metric_collectors
docker build -t taurus:latest taurus
docker build -t taurus-dynamodb:latest taurus/external/dynamodb_test_tool
