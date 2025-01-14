# ClamAV

## Description
[ClamAV](https://docs.clamav.net/) is an open-source antivirus that can be used by Iaso to scan files that are uploaded by users.

It uses a local Unix socket or a TCP socket. Be careful about how the Iaso-ClamAV connection is configured, there are security risks.


## Local ClamAV server
This feature is experimental. For development, if you need a local ClamAV server, you can start one up in your docker compose by using the `docker/docker-compose-clamav.yml ` configuration file.

Replace your invocations of `docker compose` by `docker compose -f docker-compose.yml -f docker/docker-compose-clamav.yml`. You need to specify both config files. e.g. to launch the cluster:
``` bash
docker compose -f docker-compose.yml -f docker/docker-compose-clamav.yml up
```

To start scanning files, you'll need to set two environment variables in Iaso:
- `CLAMAV_ACTIVE` set to `True`, in order to tell the backend that file uploads must be scanned (default = `False`)
- `CLAMAV_FQDN` set to the address that Iaso can use to reach your ClamAV instance (`localhost` in a local installation)

Iaso and ClamAV will communicate over the default ClamAV port, `3310`, through a TCP socket.
If you need to use another port, you'll need to edit the `docker/docker-compose-clamav.yml` file and provide the new port to Iaso through the `CLAMAV_PORT` environment variable.
