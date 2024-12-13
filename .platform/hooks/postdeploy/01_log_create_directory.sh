#!/bin/bash

# Only run on the leader instance
if [ "$EB_IS_COMMAND_LEADER" == "true" ]; then
    echo "Preparing a new directory for Django logs..."
    docker exec -t $(docker ps -a -q | head -n 1) mkdir -p /var/app/log
fi