"""Minimal local read-only dashboard delivery over an injected CEO view service."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from reports.ceo_dashboard import CEODashboardRenderer


class ReadOnlyDashboardApplication:
    def __init__(self, view_provider): self.view_provider = view_provider; self.renderer = CEODashboardRenderer()

    def handle(self, method, path):
        if method != "GET": return 405, {"content-type": "application/json"}, b'{"error":"read-only"}'
        if path == "/health": return 200, {"content-type": "application/json"}, b'{"mode":"PAPER","status":"ok"}'
        if path != "/dashboard": return 404, {"content-type": "application/json"}, b'{"error":"not-found"}'
        body = self.renderer.to_json(self.view_provider()).encode("utf-8")
        return 200, {"content-type": "application/json", "cache-control": "no-store"}, body

    def serve(self, host="127.0.0.1", port=8765):
        application = self
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self): self._respond("GET")
            def do_POST(self): self._respond("POST")
            def do_PUT(self): self._respond("PUT")
            def do_DELETE(self): self._respond("DELETE")
            def _respond(self, method):
                status, headers, body = application.handle(method, self.path)
                self.send_response(status)
                for key, value in headers.items(): self.send_header(key, value)
                self.end_headers(); self.wfile.write(body)
            def log_message(self, *_): pass
        return ThreadingHTTPServer((host, port), Handler)

