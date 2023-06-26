# -*- coding: utf-8 -*-
#
# Copyright 2023 NXP
#
# SPDX-License-Identifier: MIT


from urllib.parse import urlparse

import etcd3
from tenacity import retry, stop_after_attempt, wait_fixed


class Etcd:
    def __init__(self, endpoint_urls, timeout=5):
        grpc_options = {
            "grpc.enable_http_proxy": 0,
        }
        endpoints = []

        for url in endpoint_urls.split(","):
            url = urlparse(url)
            endpoints.append(
                etcd3.Endpoint(
                    host=url.hostname,
                    port=url.port,
                    secure=False,
                    opts=grpc_options.items(),
                )
            )

        self.etcd = etcd3.MultiEndpointEtcd3Client(
            endpoints=endpoints, timeout=timeout, failover=True
        )

        Etcd.DeleteEvent = etcd3.events.DeleteEvent
        Etcd.PutEvent = etcd3.events.PutEvent

    def __call__(self):
        return self.etcd

    @retry(wait=wait_fixed(1), stop=stop_after_attempt(3))
    def put(self, key, value):
        return self.etcd.put(key, value)

    @retry(wait=wait_fixed(1), stop=stop_after_attempt(3))
    def get(self, key, **kwargs):
        return self.etcd.get(key, **kwargs)

    @retry(wait=wait_fixed(1), stop=stop_after_attempt(3))
    def add_watch_prefix_callback(self, key_prefix, callback, **kwargs):
        return self.etcd.add_watch_prefix_callback(key_prefix, callback, **kwargs)

    @retry(wait=wait_fixed(1), stop=stop_after_attempt(3))
    def get_prefix(self, key_prefix, **kwargs):
        return self.etcd.get_prefix(key_prefix, **kwargs)
