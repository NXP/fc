#!/usr/bin/env bash

set -x

find . -path ./docker -o -path ./doc -prune -o -name "*.py" -print | xargs pylint

