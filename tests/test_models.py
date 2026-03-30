"""Tests for Invoice model business logic -- overdue detection, effective status."""

from datetime import date, timedelta

import pytest

from invoicegen.models import Invoice, InvoiceStatus


class TestOverdueDetection:
    """Invoice.is_overdue must flag unpaid invoices past their due date."""

    def test_paid_invoice_never_overdue(self):
        """A paid invoice is never overdue, even if past due date."""
        inv = Invoice(
            status=InvoiceStatus.PAID.value,
            due_date=(date.today() - timedelta(days=60)).isoformat(),
        )
        assert inv.is_overdue is False

    def test_unpaid_past_due_is_overdue(self):
        """An unpaid invoice past its due date is overdue."""
        inv = Invoice(
            status=InvoiceStatus.SENT.value,
            due_date=(date.today() - timedelta(days=1)).isoformat(),
        )
        assert inv.is_overdue is True

    def test_unpaid_future_due_not_overdue(self):
        """An unpaid invoice with a future due date is not overdue."""
        inv = Invoice(
            status=InvoiceStatus.SENT.value,
            due_date=(date.today() + timedelta(days=30)).isoformat(),
        )
        assert inv.is_overdue is False

    def test_due_today_not_overdue(self):
        """An invoice due today is not yet overdue (overdue is strictly past)."""
        inv = Invoice(
            status=InvoiceStatus.DRAFT.value,
            due_date=date.today().isoformat(),
        )
        assert inv.is_overdue is False

    def test_invalid_due_date_not_overdue(self):
        """Bad date format returns False instead of crashing."""
        inv = Invoice(status=InvoiceStatus.SENT.value, due_date="not-a-date")
        assert inv.is_overdue is False

    def test_none_due_date_not_overdue(self):
        """None due date returns False instead of crashing."""
        inv = Invoice(status=InvoiceStatus.SENT.value, due_date=None)
        assert inv.is_overdue is False


class TestEffectiveStatus:
    """Invoice.effective_status must reflect overdue state automatically."""

    def test_paid_stays_paid(self):
        """Paid invoices always show Paid regardless of due date."""
        inv = Invoice(
            status=InvoiceStatus.PAID.value,
            due_date=(date.today() - timedelta(days=90)).isoformat(),
        )
        assert inv.effective_status == "Paid"

    def test_sent_past_due_shows_overdue(self):
        """A Sent invoice past due date shows Overdue."""
        inv = Invoice(
            status=InvoiceStatus.SENT.value,
            due_date=(date.today() - timedelta(days=5)).isoformat(),
        )
        assert inv.effective_status == "Overdue"

    def test_draft_future_shows_draft(self):
        """A Draft invoice not yet due shows Draft."""
        inv = Invoice(
            status=InvoiceStatus.DRAFT.value,
            due_date=(date.today() + timedelta(days=30)).isoformat(),
        )
        assert inv.effective_status == "Draft"

    def test_sent_future_shows_sent(self):
        """A Sent invoice not yet due shows Sent."""
        inv = Invoice(
            status=InvoiceStatus.SENT.value,
            due_date=(date.today() + timedelta(days=15)).isoformat(),
        )
        assert inv.effective_status == "Sent"
