#!/usr/bin/env bash

set -x

# prctl depends on libcap development headers
sudo apt-get update
sudo apt-get install -y libcap-dev

pip3 install -r requirements/ci-requirements.txt
