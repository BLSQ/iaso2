#!/bin/bash
set -e

# Simple script to wait for DBs to have been started

until PGPASSWORD=$RDS_PASSWORD psql -h $RDS_HOSTNAME -U $RDS_USERNAME $RDS_DB_NAME -p $RDS_PORT -c '\l' > /dev/null; do
  >&2 echo "Waiting for postgres..."
  sleep 1
done

