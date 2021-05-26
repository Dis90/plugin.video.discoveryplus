import socket
import requests
import threading
import http
from http import HTTPStatus
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from io import BytesIO

from urllib.parse import urlparse, parse_qs, urlencode

import xbmcaddon, xbmc

import traceback

try:
    import zlib
except ImportError:
    zlib = None

def zlib_producer(fileobj, wbits):
    bufsize = 2 << 17
    producer = zlib.compressobj(wbits=wbits)
    with fileobj:
        while True:
            buf = fileobj.read(bufsize)
            if not buf:
                yield producer.flush()
                return
            yield producer.compress(buf)

def gzip_producer(fileobj):
    return zlib_producer(fileobj, 31)

def deflate_producer(fileobj):
    return zlib_producer(fileobj, 15)
 
class HLSProxyServer(ThreadingHTTPServer):
    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        self.s = requests.Session()
        super(ThreadingHTTPServer, self).__init__(server_address, RequestHandlerClass, bind_and_activate=True)

    def handle_error(self, request, client_address):
        print(repr(request))

class HLSProxyRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    compressions = {}
    if zlib:
        compressions = {
            "deflate": deflate_producer,
            "gzip": gzip_producer,
            "x-gzip": gzip_producer,
        }

    def make_chunk(self, data):
        return f"{len(data):X}".encode("ascii") + b"\r\n" + data + b"\r\n"

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        url = urlparse(self.path)
        path = url.path
        query = parse_qs(url.query)
        
        request_headers = {}
        if "Origin" in self.headers:
            request_headers["Origin"] = self.headers["Origin"]
        if "Referer" in self.headers:
            request_headers["Referer"] = self.headers["Referer"]
        if "User-Agent" in self.headers:
            request_headers["User-Agent"] = self.headers["User-Agent"]

        response = None
        ctype = None
        try:
            if path == "/dplus_proxy.m3u8":
                origin_url = query["hls_origin_url"][0]
                r = self.server.s.get(origin_url, headers=request_headers, timeout=5)
                r.raise_for_status()
                m3u8 = r.text
                if "old_framerate" in query:
                    m3u8 = m3u8.replace(query["old_framerate"][0], query["new_framerate"][0])
                response = BytesIO(m3u8.encode("utf-8"))
                ctype = r.headers["Content-Type"]
            else:
                self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)
                self.end_headers()
                return
        except:
            traceback.print_exc()
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.end_headers()
            return

        self.send_response_only(HTTPStatus.OK)
        self.send_header("Content-type", ctype)

        if type(response) == BytesIO:
            accept_encoding = self.headers.get_all("Accept-Encoding", ())
            encodings = {}
            for accept in http.cookiejar.split_header_words(accept_encoding):
                params = iter(accept)
                encoding = next(params, ("", ""))[0]
                quality, value = next(params, ("", ""))
                if quality == "q" and value:
                    try:
                        q = float(value)
                    except ValueError:
                        q = 0
                else:
                    q = 1
                if q:
                    encodings[encoding] = max(encodings.get(encoding, 0), q)

            compressions = set(encodings).intersection(self.compressions)
            compression = None
            if compressions:
                compression = max((encodings[enc], enc) for enc in compressions)[1]
            elif "*" in encodings and self.compressions:
                compression = list(self.compressions)[1]
            else:
                compression = list(self.compressions)[1]
            if compression:
                producer = self.compressions[compression]
                self.send_header("Content-Encoding", compression)
                self.send_header("Transfer-Encoding", "chunked")
                self.end_headers()
                if self.command == "GET":
                    for data in producer(response):
                        if data:
                            self.wfile.write(self.make_chunk(data))
                        else:
                            continue
                    self.wfile.write(self.make_chunk(b""))
        else:
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()

            if self.command == "GET":
                for data in response.iter_content(chunk_size=1024):
                    self.wfile.write(self.make_chunk(data))
                self.wfile.write(self.make_chunk(b""))

def main():
    host = ("127.0.0.1", 48201)
    hls_proxy = f"http://{host[0]}:{host[1]}/"
    server = HLSProxyServer(host, HLSProxyRequestHandler)
    httpd = threading.Thread(target=server.serve_forever)
    httpd.setDaemon(1)
    httpd.start()
    xbmc.log(f"Discovery+ HLS Proxy running at {hls_proxy}", xbmc.LOGINFO)
    while not monitor.abortRequested():
        if monitor.waitForAbort(1):
            break
    server.shutdown()
    httpd.join(5)
