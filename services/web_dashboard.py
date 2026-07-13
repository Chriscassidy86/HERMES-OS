"""Business-free composition boundary for local dashboard presentation."""
from decimal import Decimal
from models.web_dashboard import WebDashboardProjection
class WebDashboardService:
 def __init__(self,command_center,version="V4 development"): self.command_center=command_center; self.version=version
 def build(self,*,multi_timeframe=None,executive_brief=None,learning_explanation=None,experiment_status=None,research_run=None):
  view=self.command_center.build(); exposure=sum((Decimal(str(item.get("quantity",0)))*Decimal(str(item.get("current_price",0))) for item in view.open_positions),Decimal("0"))
  warnings=tuple(view.disagreements)+tuple(view.exclusions)+tuple(view.notices)
  return WebDashboardProjection(view.banner,"PAPER",self.version,view.system_health,view.provider_health,view.database_health,view.latest_cycle,view.market_regime,multi_timeframe,view.specialists,view.agreements,view.disagreements,view.exclusions,view.risk_decision,str(view.cash),str(view.equity),str(exposure),view.open_positions,view.closed_trades,str(view.daily_pnl),str(view.weekly_pnl),str(view.total_return),str(view.drawdown),str(view.win_rate),str(view.profit_factor) if view.profit_factor is not None else None,warnings,executive_brief,learning_explanation,experiment_status,research_run)
