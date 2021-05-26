# -*- coding: utf-8 -*-

import threading

import resources.service.proxy as proxy

proxy_th = threading.Thread(target=proxy.main)

proxy_th.start()
