"""Expose only GET /metrics on 30001; inference stays on protected port 30000.

Runs as a non-root sidecar using the already pinned runtime image. Fixed upstream
and exact path matching prevent using this proxy for inference or arbitrary URLs.
This small lab proxy is not an enterprise gateway. Request logging is disabled.
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.request


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path != '/metrics':
            self.send_error(404)
            return
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open('http://127.0.0.1:30000/metrics', timeout=5) as upstream:
                data = upstream.read(2 * 1024 * 1024 + 1)
            if len(data) > 2 * 1024 * 1024:
                raise ValueError('Oversized metrics')
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; version=0.0.4')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception:
            self.send_error(502, 'Metrics unavailable')


class Server(HTTPServer):
    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(5)  # An idle client must not monopolize the lab proxy.
        return connection, address


if __name__ == '__main__':
    Server(('0.0.0.0', 30001), Handler).serve_forever()
