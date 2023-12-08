#!/bin/bash
set -e

# This script is used as the entrypoint for docker when used for local dev

show_help() {
  echo """
  Commands
  ---------------------------------------------------------------

  start            : start django + uwsgi
  start_dev        : start django devserver
  start_webpack    : start webpack server (only in DEV mode)

  manage           : run django manage.py
  eval             : eval shell command
  bash             : run bash
  """
}

export PYTHONPATH="/opt/app:$PYTHONPATH"

if [ -e hat/local_settings.py ]
then
    export DJANGO_SETTINGS_MODULE=hat.local_settings
else
    export DJANGO_SETTINGS_MODULE=hat.settings
fi

case "$1" in
  "start")
    ./scripts/wait_for_dbs.sh
    ./manage.py migrate --noinput
    ./manage.py runserver 0.0.0.0:8081
    ;;
  "start_gunicorn")
    ./scripts/wait_for_dbs.sh
    ./manage.py migrate --noinput
    gunicorn hat.wsgi --workers 5 --threads=10 --bind=0.0.0.0:8081 --timeout 600
  ;;
  "test" )
    export TESTING=true
    # Linting tasks first
    flake8 ./hat
    npm run lint
    # Then tests
    ./scripts/wait_for_dbs.sh
    # Run python tests and pass on any args to e.g. run individual tests
    ./manage.py test --exclude-tag selenium "${@:2}"
    npm run mocha
  ;;
  "test_lint" )
    export TESTING=true
    flake8 ./hat -v
    npm run lint
  ;;
  "test_js" )
    npm run test
  ;;
  "mocha" )
    npm run mocha
  ;;
  "gen_docs" )
    ./scripts/gen_docs.sh
  ;;
  "start_dev" )
    export DEV_SERVER=true
    ./scripts/wait_for_dbs.sh
    ./manage.py migrate --noinput
    ./manage.py createcachetable
    ./manage.py compilemessages
    ./manage.py runserver 0.0.0.0:8081
  ;;
  "start_celery_beat" )
    celery -A hat beat -l info --scheduler "django_celery_beat.schedulers:DatabaseScheduler"
  ;;
  "start_celery_worker" )
    celery -A hat worker -l info --without-heartbeat
  ;;
  "start_webpack" )
    # if TEST_PROD, make a static js bundle otherwise launch js dev server
    if [ -n "$TEST_PROD" ]; then
      npm run webpack-prod
      exit 0
    fi

    npm run webpack-server
  ;;
  "start_dev_couchdb_nginx" )
    # ssl proxy to web
    envsubst "\$COUCHDB_URL" < ./plugins/trypelim/build_scripts/local/nginx-ssl.conf.local > /etc/nginx/sites-available/default
    cp ./plugins/trypelim/build_scripts/local/nginx.key.local /etc/nginx/cert.key
    cp ./plugins/trypelim/build_scripts/local/nginx.crt.local /etc/nginx/cert.crt
    nginx -g "daemon off;"
  ;;

  "manage" )
    ./manage.py "${@:2}"
  ;;
  "eval" )
    eval "${@:2}"
  ;;
  "bash" )
    bash
  ;;
  "python" )
    python "${@:2}"
  ;;
  * )
    show_help
  ;;
esac
