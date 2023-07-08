# -*- coding: utf-8 -*-

import threading

import resources.services.realmservice as realmservice
import resources.services.pseudotv_recommended as pseudotv

realmservice_th = threading.Thread(target=realmservice.main)
pseudo_th = threading.Thread(target=pseudotv.regPseudoTV)

realmservice_th.start()
pseudo_th.start()