#!/usr/bin/env bash

set -x

declare ROOT_HOME="$(cd "$(cd "$(dirname "$0")"; pwd -P)"/..; pwd)"

version=$(cat $ROOT_HOME/fc_common/VERSION)

cd $ROOT_HOME

docker push atline/fc-client:$version
docker push atline/fc-client
docker push atline/fc-server:$version
docker push atline/fc-guarder:$version

