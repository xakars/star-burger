#!/bin/bash

source .env

git pull

latest_commit=$(git rev-parse HEAD)

sudo docker compose up -d

curl -H "X-Rollbar-Access-Token:$ROLLBAR_TOKEN" -H "Content-Type: application/json" -X POST 'https://api.rollbar.com/api/1/deploy' -d '{"environment": "'"$ENVIRONMENT"'", "revision": "'"$latest_commit"'", "rollbar_name": "xakars02", "local_username": "lon_server", "comment": "deployment", "status": "succeeded"}'


