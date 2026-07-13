"""Validated read-only chart projections over supplied persisted rows."""
from datetime import datetime,timezone
from math import ceil,isfinite
from models.visualization import ChartPoint,ChartSeries
class VisualizationService:
 def build(self,name,rows,*,value_key,source_label,offset=0,limit=500,max_points=200):
  if source_label not in {"FIXTURE","REPLAY","PUBLIC_OBSERVATION","PAPER"}: raise ValueError("Chart source label is invalid.")
  if offset<0 or limit<1 or max_points<1: raise ValueError("Chart pagination is invalid.")
  values=[]
  for row in rows:
   timestamp=row.get("timestamp"); timestamp=datetime.fromisoformat(timestamp) if isinstance(timestamp,str) else timestamp; value=row.get(value_key)
   if not isinstance(timestamp,datetime) or timestamp.tzinfo is None or isinstance(value,bool) or not isinstance(value,(int,float)) or not isfinite(value): raise ValueError("Chart row is malformed.")
   metadata=tuple(sorted((str(k),str(v)) for k,v in row.items() if k not in {"timestamp",value_key}))
   values.append(ChartPoint(timestamp.astimezone(timezone.utc).isoformat(),float(value),metadata))
  values.sort(key=lambda item:item.timestamp); total=len(values); page=values[offset:offset+limit]
  if len(page)>max_points:
   step=ceil(len(page)/max_points); page=page[::step]
  state="EMPTY" if not page else ("INSUFFICIENT_DATA" if total==1 else "READY")
  return ChartSeries(name,source_label,tuple(page),state,"Historical paper, fixture, replay, or observation data does not guarantee profitability.",total,offset,limit)
