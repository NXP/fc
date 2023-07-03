#!/usr/bin/env bash

set -x

declare ROOT_HOME="$(cd "$(cd "$(dirname "$0")"; pwd -P)"/..; pwd)"

python3 $ROOT_HOME/setup.py clean
python3 $ROOT_HOME/setup.py sdist fc-server
python3 $ROOT_HOME/setup.py sdist fc-guarder
python3 $ROOT_HOME/setup.py sdist fc-client
python3 $ROOT_HOME/setup.py sdist fc-client-docker
