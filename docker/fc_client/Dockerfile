FROM python:3.9-buster

RUN pip install fc-client; \
apt-get update; \
apt-get install -y microcom corkscrew; \
rm -rf /var/lib/apt/lists/*;
