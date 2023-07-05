FROM python:3.9-buster

WORKDIR /fc

RUN apt-get update; \
apt-get install -y microcom corkscrew; \
rm -rf /var/lib/apt/lists/*;

COPY requirements requirements
RUN pip install -r requirements/client-requirements.txt

COPY docker/fc_client/fc-client /bin
RUN chmod +x /bin/fc-client

COPY fc_common fc_common
COPY fc_client fc_client
COPY fc_client_daemon fc_client_daemon

WORKDIR /root
