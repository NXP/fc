FROM python:3.9-buster

RUN pip install lavacli==1.2 labgrid==0.4.0; \
pip uninstall -y pyserial; \
pip install https://github.com/labgrid-project/pyserial/archive/v3.4.0.1.zip#egg=pyserial

WORKDIR /fc
COPY . .
RUN chmod +x /fc/docker/entrypoint.sh
RUN pip install -r requirements.txt

ENV REQUESTS_CA_BUNDLE='/etc/ssl/certs/ca-certificates.crt'

CMD ["/fc/docker/entrypoint.sh"]

