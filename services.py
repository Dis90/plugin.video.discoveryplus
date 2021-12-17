# -*- coding: utf-8 -*-

import threading

import resources.services.realmservice as realmservice

realmservice_th = threading.Thread(target=realmservice.main)

realmservice_th.start()