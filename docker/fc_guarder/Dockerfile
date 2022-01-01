FROM python:3.9-buster

RUN pip install lavacli==1.2

WORKDIR /fc
COPY . .
RUN chmod +x /fc/docker/fc_guarder/entrypoint.sh

ENV REQUESTS_CA_BUNDLE='/etc/ssl/certs/ca-certificates.crt'

CMD ["/fc/docker/fc_guarder/entrypoint.sh"]

