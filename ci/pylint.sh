#!/usr/bin/env bash

set -x

find . -name "*.py" | xargs pylint
