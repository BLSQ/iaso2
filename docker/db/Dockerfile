FROM postgres:16

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install postgis postgresql-16-postgis-3 -y \
 && rm -rf /var/lib/apt/lists/*


RUN mkdir -p /docker-entrypoint-initdb.d
COPY ./initdb-postgis.sh /docker-entrypoint-initdb.d/postgis.sh
COPY ./update-postgis.sh /usr/local/bin