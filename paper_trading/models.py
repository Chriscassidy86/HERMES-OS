"""Immutable paper-trading records. These models cannot contact an exchange."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

class OrderStatus(str, Enum):
    CREATED="CREATED"; VALIDATED="VALIDATED"; REJECTED="REJECTED"; OPEN="OPEN"
    PARTIALLY_FILLED="PARTIALLY_FILLED"; FILLED="FILLED"; CANCELLED="CANCELLED"; CLOSED="CLOSED"

@dataclass(frozen=True)
class PaperAccount:
    cash_balance: Decimal
    equity_balance: Decimal

@dataclass(frozen=True)
class PaperPosition:
    symbol: str
    quantity: Decimal
    average_entry_price: Decimal
    current_price: Decimal
    entry_fees: Decimal = Decimal("0")
    side: str = "LONG"

    def __post_init__(self):
        if self.side not in {"LONG", "SHORT"}:
            raise ValueError("Paper position side must be LONG or SHORT.")

    @property
    def market_value(self):
        if self.side == "SHORT":
            return -(self.quantity * self.current_price)
        return self.quantity * self.current_price

    @property
    def unrealized_pnl(self):
        if self.side == "SHORT":
            return (
                (self.average_entry_price - self.current_price)
                * self.quantity
                - self.entry_fees
            )
        return (
            (self.current_price - self.average_entry_price)
            * self.quantity
            - self.entry_fees
        )

@dataclass(frozen=True)
class PaperOrder:
    order_id: str; cycle_id: str; symbol: str; side: str; quantity: Decimal
    reference_price: Decimal; status: OrderStatus; created_at: datetime
    rejection_reasons: tuple[str,...]=()

@dataclass(frozen=True)
class PaperFill:
    fill_id: str; order_id: str; quantity: Decimal; price: Decimal
    fee: Decimal; slippage: Decimal; timestamp: datetime

@dataclass(frozen=True)
class PaperTrade:
    trade_id: str; symbol: str; quantity: Decimal; entry_price: Decimal
    exit_price: Decimal; fees: Decimal; realized_pnl: Decimal; closed_at: datetime

@dataclass(frozen=True)
class OrderTransition:
    order_id: str; previous_status: OrderStatus; new_status: OrderStatus
    timestamp: datetime; reason: str
