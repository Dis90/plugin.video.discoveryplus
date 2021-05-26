# -*- coding: utf-8 -*-

import threading

import resources.service.proxy as proxy
import pseudotv_recommended as pseudotv

proxy_th = threading.Thread(target=proxy.main)
psuedo_th = threading.Thread(target=pseudotv.regPseudoTV)

proxy_th.start()
psuedo_th.start()

#proxy.main()
#psuedotv.regPseudoTV()