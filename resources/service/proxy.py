# thanks to matthuisman for the example at https://github.com/matthuisman/proxy.plugin.example

import threading

import xbmc
import requests

try:
    # Python3
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from socketserver import ThreadingMixIn
    from urllib.parse import urlparse, parse_qs
except:
    # Python2
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
    from SocketServer import ThreadingMixIn
    from urlparse import urlparse, parse_qs

HOST = '127.0.0.1'
PORT = 48201
REMOVE_IN_HEADERS = ['upgrade', 'host']
REMOVE_OUT_HEADERS = ['date', 'server', 'transfer-encoding', 'keep-alive', 'connection', 'content-length', 'content-encoding']

class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_POST(self):
        self.send_error(404)

    def do_HEAD(self):
        self.send_error(404)

    def do_GET(self):
        url = urlparse(self.path)
        path = url.path
        query = parse_qs(url.query)
        if not path == "/dplus_proxy.m3u8":
            self.send_error(404)

        headers = {}
        for key in self.headers:
            if key.lower() not in REMOVE_IN_HEADERS:
                headers[key] = self.headers[key]
        
        origin_url = query["hls_origin_url"][0]

        response = requests.get(origin_url, headers=headers, timeout=5)

        self.send_response(response.status_code)

        for key in response.headers:
            if key.lower() not in REMOVE_OUT_HEADERS:
                self.send_header(key, response.headers[key])

        self.end_headers()

        ## Edit the content
        content = response.content.decode('utf8')
        if "old_framerate" in query:
            content = content.replace(query["old_framerate"][0], query["new_framerate"][0])
        # Output the content
        self.wfile.write(content.encode('utf8'))

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
