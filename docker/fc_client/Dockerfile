FROM python:3.9-buster

RUN pip install fc-client; \
pip uninstall -y pyserial; \
pip install https://github.com/labgrid-project/pyserial/archive/v3.4.0.1.zip#egg=pyserial; \
apt-get update; \
apt-get install -y microcom corkscrew; \
rm -rf /var/lib/apt/lists/*;
