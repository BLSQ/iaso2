#!/bin/bash

# Only run on the leader instance
if [ "$EB_IS_COMMAND_LEADER" == "true" ]; then
    echo "Changing permissions on the Django logs directory..."
    docker exec -t $(docker ps -a -q | head -n 1) chmod g+s /var/app/log
fi