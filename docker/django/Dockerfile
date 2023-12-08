# https://hub.docker.com/_/python
FROM python:3.9

RUN apt-get update && apt-get --yes install \
		curl \
		gettext \
		gettext-base \
		postgresql-client \
		libgdal-dev \
		nginx \
    &&  apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY plugins/trypelim/build_scripts/nginx.conf /etc/nginx/sites-available/default

WORKDIR /opt/app

# install python dependencies
COPY requirements.txt /opt/app/requirements.txt
COPY requirements-dev.txt /opt/app/requirements-dev.txt
RUN pip install -r requirements-dev.txt

# don't copy app we mount everything afterwards for hot reloading anyway
#COPY . /opt/app

ENTRYPOINT ["/opt/app/entrypoint.sh"]
