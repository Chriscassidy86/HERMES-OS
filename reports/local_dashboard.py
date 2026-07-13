"""Minimal local read-only dashboard delivery over an injected CEO view service."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from reports.ceo_dashboard import CEODashboardRenderer
from reports.web_dashboard import WebDashboardRenderer


class ReadOnlyDashboardApplication:
    def __init__(self, view_provider, chart_provider=None): self.view_provider = view_provider; self.chart_provider=chart_provider; self.renderer = CEODashboardRenderer(); self.web_renderer=WebDashboardRenderer()

    def handle(self, method, path):
        if method != "GET": return 405, {"content-type": "application/json"}, b'{"error":"read-only"}'
        if path in {"/health","/api/health"}: return 200, {"content-type": "application/json"}, b'{"mode":"PAPER","status":"ok"}'
        if path=="/api/charts":
            if self.chart_provider is None: return 200,{"content-type":"application/json"},b'{"charts":[]}'
            import json
            from dataclasses import asdict
            return 200,{"content-type":"application/json","cache-control":"no-store"},json.dumps({"charts":[asdict(item) for item in self.chart_provider()]},sort_keys=True,separators=(",",":")).encode()
        if path in {"/","/dashboard.html"}:
            view=self.view_provider(); body=(self.web_renderer.html(view) if hasattr(view,"latest_decision") else '<h1>PAPER MODE ONLY</h1><pre>'+self.renderer.to_json(view)+'</pre>').encode("utf-8"); return 200,{"content-type":"text/html; charset=utf-8","cache-control":"no-store"},body
        if path not in {"/dashboard","/api/dashboard"}: return 404, {"content-type": "application/json"}, b'{"error":"not-found"}'
        view=self.view_provider(); body=(self.web_renderer.json(view) if hasattr(view,"latest_decision") else self.renderer.to_json(view)).encode("utf-8")
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

