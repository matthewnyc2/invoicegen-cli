"""Data models for InvoiceGen."""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Optional


class InvoiceStatus(str, Enum):
    DRAFT = "Draft"
    SENT = "Sent"
    PAID = "Paid"
    OVERDUE = "Overdue"


@dataclass
class Client:
    id: Optional[int] = None
    name: str = ""
    email: str = ""
    address: str = ""
    phone: str = ""
    created_at: str = ""


@dataclass
class LineItem:
    id: Optional[int] = None
    invoice_id: Optional[int] = None
    description: str = ""
    amount: float = 0.0


@dataclass
class Invoice:
    id: Optional[int] = None
    invoice_number: str = ""
    client_id: Optional[int] = None
    client_name: str = ""
    client_email: str = ""
    client_address: str = ""
    status: str = InvoiceStatus.DRAFT.value
    subtotal: float = 0.0
    tax_rate: float = 0.0
    tax_amount: float = 0.0
    total: float = 0.0
    created_at: str = ""
    due_date: str = ""
    paid_at: Optional[str] = None
    notes: str = ""
    items: list = field(default_factory=list)

    @property
    def is_overdue(self) -> bool:
        if self.status == InvoiceStatus.PAID.value:
            return False
        try:
            due = datetime.strptime(self.due_date, "%Y-%m-%d").date()
            return date.today() > due
        except (ValueError, TypeError):
            return False

    @property
    def effective_status(self) -> str:
        if self.status == InvoiceStatus.PAID.value:
            return InvoiceStatus.PAID.value
        if self.is_overdue:
            return InvoiceStatus.OVERDUE.value
        return self.status
