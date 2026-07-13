"""Localhost-only, GET-only delivery for the immutable web projection."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from dataclasses import asdict
import json
from urllib.parse import urlsplit

from reports.web_dashboard import WebDashboardRenderer


class ReadOnlyDashboardApplication:
    def __init__(self, view_provider, chart_provider=None, *, allow_container_bridge=False): self.view_provider = view_provider; self.chart_provider=chart_provider; self.allow_container_bridge=allow_container_bridge; self.web_renderer=WebDashboardRenderer()

    def handle(self, method, path):
        if method != "GET": return 405, {"content-type": "application/json"}, b'{"error":"read-only"}'
        path=urlsplit(path).path
        if path in {"/health","/api/health"}: return 200, {"content-type": "application/json"}, b'{"mode":"PAPER","status":"ok"}'
        if path=="/api/charts":
            if self.chart_provider is None: return 200,{"content-type":"application/json"},b'{"charts":[]}'
            return 200,{"content-type":"application/json","cache-control":"no-store"},json.dumps({"charts":[asdict(item) for item in self.chart_provider()]},sort_keys=True,separators=(",",":")).encode()
        if path in {"/","/dashboard.html"}:
            view=self.view_provider(); body=self.web_renderer.html(view).encode("utf-8")
            return 200,{"content-type":"text/html; charset=utf-8","cache-control":"no-store","x-content-type-options":"nosniff"},body
        endpoints={
            "/api/portfolio": ("starting_balance","cash","equity","total_return","realized_pnl","unrealized_pnl","exposure","open_positions","closed_trades"),
            "/api/providers": ("active_provider","provider_health","providers"),
            "/api/trades": ("recent_fills","recent_trades","closed_trades"),
            "/api/alerts": ("recent_alerts","warnings"),
        }
        if path in {"/dashboard","/api/dashboard"}:
            body=self.web_renderer.json(self.view_provider()).encode("utf-8")
        elif path in endpoints:
            data=asdict(self.view_provider()); payload={key:data[key] for key in endpoints[path]}
            body=json.dumps(payload,default=str,sort_keys=True,separators=(",",":")).encode("utf-8")
        else:
            return 404, {"content-type": "application/json"}, b'{"error":"not-found"}'
        return 200, {"content-type": "application/json", "cache-control": "no-store","x-content-type-options":"nosniff"}, body

    def serve(self, host="127.0.0.1", port=8765):
        if host != "127.0.0.1" and not (self.allow_container_bridge and host == "0.0.0.0"):
            raise ValueError("Dashboard binding is restricted to 127.0.0.1.")
        if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
            raise ValueError("Dashboard port is invalid.")
        application = self
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self): self._respond("GET")
            def do_POST(self): self._respond("POST")
            def do_PUT(self): self._respond("PUT")
            def do_PATCH(self): self._respond("PATCH")
            def do_DELETE(self): self._respond("DELETE")
            def _respond(self, method):
                status, headers, body = application.handle(method, self.path)
                self.send_response(status)
                for key, value in headers.items(): self.send_header(key, value)
                self.end_headers(); self.wfile.write(body)
            def log_message(self, *_): pass
        return ThreadingHTTPServer((host, port), Handler)

