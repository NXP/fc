FROM python:3.9-buster

WORKDIR /fc

RUN apt-get update; \
apt-get install -y libcap-dev; \
rm -rf /var/lib/apt/lists/*;

COPY requirements requirements
RUN pip install -r requirements/server-requirements.txt

COPY docker docker
RUN chmod +x /fc/docker/fc_server/entrypoint.sh

COPY fc_common fc_common
COPY fc_server fc_server
COPY fc_server_daemon fc_server_daemon

ENV REQUESTS_CA_BUNDLE='/etc/ssl/certs/ca-certificates.crt'
ENV PYTHONPATH=.

CMD ["/fc/docker/fc_server/entrypoint.sh"]
