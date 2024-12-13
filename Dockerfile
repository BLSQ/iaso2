FROM ghcr.io/blsq/iaso:fab1e7cd4f3994f914db9e0665d8cb00671ea73e

EXPOSE 8081

ENTRYPOINT ./entrypoint.sh start_gunicorn
