"""Stable JSON and HTML-only rendering for the local web dashboard."""
from dataclasses import asdict
import html,json
from models.web_dashboard import WebDashboardProjection
class WebDashboardRenderer:
 def json(self,view): return json.dumps(asdict(view),default=str,sort_keys=True,separators=(",",":"))
 def html(self,view):
  data=asdict(view); sections=[]
  for key,value in data.items(): sections.append(f'<section id="{html.escape(key)}"><h2>{html.escape(key.replace("_"," ").title())}</h2><pre>{html.escape(json.dumps(value,default=str,sort_keys=True,indent=2))}</pre></section>')
  return '<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="refresh" content="5"><title>Hermes Live PAPER Dashboard</title></head><body><header><h1>PAPER MODE ONLY</h1></header>'+''.join(sections)+'</body></html>'
