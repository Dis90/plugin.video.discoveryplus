# -*- coding: utf-8 -*-

import threading

import resources.services.realmservice as realmservice
import pseudotv_recommended as pseudotv

realmservice_th = threading.Thread(target=realmservice.main)
psuedo_th = threading.Thread(target=pseudotv.regPseudoTV)

realmservice_th.start()
psuedo_th.start()