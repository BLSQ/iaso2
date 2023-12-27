#!/bin/bash

################################################################################
# Note: this is the exact same file as in the .platform/confighooks folder.
# The script in confighooks is executed upon configuration changes such as changing
# ENV variables. This file is executed on deploy.
# We need to run this in both situations and I couldn't find a way to do it with 1 file.
################################################################################

# Since we want to use the env var COUCHDB_URL, we cannot create this file directly
# in the nginx config.

# Create new file in tmp with nginx config.
cat <<'EOF' > /tmp/02_trypelim_couchdb.conf
location /_couchdb {
  proxy_set_header Host $host;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

  rewrite /_couchdb/(.*) /$1 break;
  proxy_pass ${COUCHDB_URL};
}
EOF

# Now create the file in the desired location with the env var subsituted for the
# real couchdb URL.
envsubst '$COUCHDB_URL' < /tmp/02_trypelim_couchdb.conf > /etc/nginx/conf.d/elasticbeanstalk/02_trypelim_couchdb.conf

# End by restarting nginx
systemctl restart nginx
