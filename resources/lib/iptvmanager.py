# -*- coding: utf-8 -*-
"""IPTV Manager Integration module"""

import sys
import json
import socket

from resources.lib.kodihelper import KodiHelper

base_url = sys.argv[0]
handle = int(sys.argv[1])
helper = KodiHelper(base_url, handle)

class IPTVManager:
    """Interface to IPTV Manager"""

    def __init__(self, port):
        """Initialize IPTV Manager object"""
        self.port = port

    def via_socket(func):
        """Send the output of the wrapped function to socket"""

        def send(self):
            """Decorator to send over a socket"""
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('127.0.0.1', self.port))
            try:
                sock.sendall(json.dumps(func(self)).encode())
            finally:
                sock.close()

        return send

    @via_socket
    def send_channels(self):
        """Return JSON-STREAMS formatted python datastructure to IPTV Manager"""
        # go = US and Canada
        if helper.d.realm == 'go':
            streams = helper.d.get_channels_us()
        elif helper.d.realm == 'dplusindia':
            streams = helper.d.get_channels_in()
        else:
            streams = helper.d.get_channels()

        return dict(version=1, streams=streams)

    @via_socket
    def send_epg(self):
        """Return JSON-EPG formatted python data structure to IPTV Manager"""
        # go = US and Canada
        if helper.d.realm == 'go':
            epg = helper.d.get_epg_us()
        elif helper.d.realm == 'dplusindia':
            epg = helper.d.get_epg_in()
        else:
            epg = helper.d.get_epg()

        return dict(version=1, epg=epg)


