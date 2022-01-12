#!/bin/bash

update-ca-certificates

exec python /fc/fc_server/server.py
