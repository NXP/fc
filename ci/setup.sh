#!/usr/bin/env bash

set -x

apt-get -q update
apt-get install -y --no-install-recommends black isort pylint

