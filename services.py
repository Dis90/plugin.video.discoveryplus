# -*- coding: utf-8 -*-

import threading

import resources.services.realmservice as realmservice
import resources.services.pseudotv_recommended as pseudotv
import resources.services.proxy as proxy

realmservice_th = threading.Thread(target=realmservice.main)
pseudo_th = threading.Thread(target=pseudotv.regPseudoTV)
proxy_th = threading.Thread(target=proxy.main)

realmservice_th.start()
pseudo_th.start()
proxy_th.start()