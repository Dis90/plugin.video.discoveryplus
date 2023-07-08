# thanks to matthuisman for the example at https://github.com/matthuisman/proxy.plugin.example

import threading

import xbmc
import requests

from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs, urljoin

HOST = '127.0.0.1'
PORT = 48201
REMOVE_IN_HEADERS = ['upgrade', 'host']
REMOVE_OUT_HEADERS = ['date', 'server', 'transfer-encoding', 'keep-alive', 'connection', 'content-length',
                      'content-encoding']


class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        url = self.path.lstrip('/').strip('\\')
        path = urljoin(url, urlparse(url).path)
        if not path.endswith(('.jpeg', '.jpg', '.png')):
            self.send_error(404)

        headers = {}
        for key in self.headers:
            if key.lower() not in REMOVE_IN_HEADERS:
                headers[key] = self.headers[key]

        response = requests.get(url)

        self.send_response(response.status_code)

        for key in response.headers:
            if key.lower() not in REMOVE_OUT_HEADERS:
                self.send_header(key, response.headers[key])

        self.end_headers()

        ## Edit the content
        content = response.content

        # Output the content
        self.wfile.write(content)

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def main():
    server = ThreadedHTTPServer((HOST, PORT), RequestHandler)
    server.allow_reuse_address = True
    httpd_thread = threading.Thread(target=server.serve_forever)
    httpd_thread.start()

    xbmc.Monitor().waitForAbort()

    server.shutdown()
    server.server_close()
    server.socket.close()
    httpd_thread.join()