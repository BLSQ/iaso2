#!/bin/bash

# Only run on the leader instance
if [ "$EB_IS_COMMAND_LEADER" == "true" ]; then
    echo "Running migrate on leader instance..."
    docker exec -t $(docker ps -a -q | head -n 1) python manage.py migrate --noinput
fi