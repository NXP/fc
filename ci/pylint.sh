#!/usr/bin/env bash

set -x

find . -path ./docker -prune -o -name "*.py" -print | xargs pylint
