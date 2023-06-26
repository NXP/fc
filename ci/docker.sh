#!/usr/bin/env bash

set -x

declare ROOT_HOME="$(cd "$(cd "$(dirname "$0")"; pwd -P)"/..; pwd)"

version=$(cat $ROOT_HOME/fc_common/VERSION)

cd $ROOT_HOME

docker build -t atline/fc-client:$version -f docker/fc_client/Dockerfile . --no-cache
docker tag atline/fc-client:$version atline/fc-client
docker build -t atline/fc-server:$version -f docker/fc_server/Dockerfile . --no-cache
docker build -t atline/fc-guarder:$version -f docker/fc_guarder/Dockerfile . --no-cache
