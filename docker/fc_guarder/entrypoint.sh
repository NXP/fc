#!/bin/bash

update-ca-certificates

exec python /fc/fc_guarder/guarder.py
