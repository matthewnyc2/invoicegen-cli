"""Tests for database layer -- CRUD operations, invoice numbering, tax calculation."""

from datetime import date, timedelta

import pytest

from invoicegen import database as db
from invoicegen.models import InvoiceStatus


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLIENT CRUD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestClientCRUD:
    def test_add_client(self):
        client = db.add_client("Acme Corp", "billing@acme.com", "123 Main St", "555-0100")
        assert client.id is not None
        assert client.name == "Acme Corp"
        assert client.email == "billing@acme.com"

    def test_add_duplicate_client_raises(self):
        db.add_client("Acme Corp")
        with pytest.raises(Exception):
            db.add_client("Acme Corp")

    def test_get_client_by_name(self):
        db.add_client("Globex Inc", "ap@globex.com")
        found = db.get_client_by_name("Globex Inc")
        assert found is not None
        assert found.email == "ap@globex.com"

    def test_get_nonexistent_client_returns_none(self):
        assert db.get_client_by_name("Ghost Corp") is None

    def test_list_clients_empty(self):
        assert db.list_clients() == []

    def test_list_clients_ordered(self):
        db.add_client("Zebra Co")
        db.add_client("Alpha LLC")
        clients = db.list_clients()
        assert clients[0].name == "Alpha LLC"
        assert clients[1].name == "Zebra Co"

    def test_delete_client(self):
        client = db.add_client("Temp Client")
        assert db.delete_client(client.id) is True
        assert db.get_client_by_name("Temp Client") is None

    def test_delete_nonexistent_returns_false(self):
        assert db.delete_client(9999) is False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INVOICE NUMBERING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestInvoiceNumbering:
    def _make_client(self):
        return db.add_client("Test Client")

    def test_first_invoice_number(self):
        """First invoice of the year gets 0001."""
        client = self._make_client()
        inv = db.create_invoice(client.id, [("Work", 100.0)])
        year = date.today().year
        assert inv.invoice_number == f"INV-{year}-0001"

    def test_sequential_numbering(self):
        """Subsequent invoices increment the counter."""
        client = self._make_client()
        inv1 = db.create_invoice(client.id, [("Work A", 100.0)])
        inv2 = db.create_invoice(client.id, [("Work B", 200.0)])
        inv3 = db.create_invoice(client.id, [("Work C", 300.0)])
        year = date.today().year
        assert inv1.invoice_number == f"INV-{year}-0001"
        assert inv2.invoice_number == f"INV-{year}-0002"
        assert inv3.invoice_number == f"INV-{year}-0003"

    def test_invoice_number_format(self):
        """Invoice numbers follow INV-YYYY-NNNN pattern."""
        client = self._make_client()
        inv = db.create_invoice(client.id, [("Item", 50.0)])
        parts = inv.invoice_number.split("-")
        assert parts[0] == "INV"
        assert len(parts[1]) == 4  # YYYY
        assert len(parts[2]) == 4  # NNNN zero-padded


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAX CALCULATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestTaxCalculation:
    def _make_client(self):
        return db.add_client("Tax Client")

    def test_zero_tax(self):
        """Default 0% tax means total equals subtotal."""
        client = self._make_client()
        inv = db.create_invoice(client.id, [("Service", 1000.0)], tax_rate=0.0)
        assert inv.subtotal == 1000.0
        assert inv.tax_amount == 0.0
        assert inv.total == 1000.0

    def test_standard_tax(self):
        """Tax is calculated as subtotal * rate / 100, rounded to 2 decimals."""
        client = self._make_client()
        inv = db.create_invoice(client.id, [("Service", 1000.0)], tax_rate=8.5)
        assert inv.subtotal == 1000.0
        assert inv.tax_rate == 8.5
        assert inv.tax_amount == 85.0
        assert inv.total == 1085.0

    def test_multiple_items_tax(self):
        """Tax applies to the sum of all line items."""
        client = self._make_client()
        items = [("Design", 2500.0), ("Dev", 3500.0), ("QA", 1000.0)]
        inv = db.create_invoice(client.id, items, tax_rate=10.0)
        assert inv.subtotal == 7000.0
        assert inv.tax_amount == 700.0
        assert inv.total == 7700.0

    def test_tax_rounding(self):
        """Tax amount is rounded to 2 decimal places."""
        client = self._make_client()
        # 333.33 * 7.75 / 100 = 25.833075 -> 25.83
        inv = db.create_invoice(client.id, [("Service", 333.33)], tax_rate=7.75)
        assert inv.tax_amount == 25.83
        assert inv.total == round(333.33 + 25.83, 2)

    def test_uses_default_tax_rate(self):
        """When no tax_rate is passed, uses the configured default."""
        db.set_setting("tax_rate", "6.0")
        client = self._make_client()
        inv = db.create_invoice(client.id, [("Work", 500.0)])
        assert inv.tax_rate == 6.0
        assert inv.tax_amount == 30.0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DUE DATE & PAYMENT TERMS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestDueDateCalculation:
    def _make_client(self):
        return db.add_client("Due Date Client")

    def test_default_net_30(self):
        """Default payment terms are Net 30."""
        client = self._make_client()
        inv = db.create_invoice(client.id, [("Work", 100.0)])
        expected_due = (date.today() + timedelta(days=30)).isoformat()
        assert inv.due_date == expected_due

    def test_custom_net_days(self):
        """Custom net_days overrides the default."""
        client = self._make_client()
        inv = db.create_invoice(client.id, [("Work", 100.0)], net_days=45)
        expected_due = (date.today() + timedelta(days=45)).isoformat()
        assert inv.due_date == expected_due

    def test_net_days_from_settings(self):
        """When no net_days passed, uses configured default."""
        db.set_setting("net_days", "60")
        client = self._make_client()
        inv = db.create_invoice(client.id, [("Work", 100.0)])
        expected_due = (date.today() + timedelta(days=60)).isoformat()
        assert inv.due_date == expected_due


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STATUS MANAGEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestStatusManagement:
    def _make_invoice(self):
        client = db.add_client("Status Client")
        return db.create_invoice(client.id, [("Work", 500.0)])

    def test_new_invoice_is_draft(self):
        """Newly created invoices start as Draft."""
        inv = self._make_invoice()
        assert inv.status == "Draft"

    def test_update_to_sent(self):
        inv = self._make_invoice()
        db.update_invoice_status(inv.id, InvoiceStatus.SENT.value)
        updated = db.get_invoice(inv.id)
        assert updated.status == "Sent"

    def test_update_to_paid_sets_paid_at(self):
        """Marking as Paid records the paid_at timestamp."""
        inv = self._make_invoice()
        db.update_invoice_status(inv.id, InvoiceStatus.PAID.value)
        updated = db.get_invoice(inv.id)
        assert updated.status == "Paid"
        assert updated.paid_at is not None

    def test_update_from_paid_to_sent_clears_paid_at(self):
        """Changing from Paid to another status clears paid_at."""
        inv = self._make_invoice()
        db.update_invoice_status(inv.id, InvoiceStatus.PAID.value)
        db.update_invoice_status(inv.id, InvoiceStatus.SENT.value)
        updated = db.get_invoice(inv.id)
        assert updated.status == "Sent"
        assert updated.paid_at is None

    def test_update_nonexistent_returns_false(self):
        assert db.update_invoice_status(9999, "Paid") is False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LINE ITEMS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestLineItems:
    def test_invoice_stores_items(self):
        """Invoice retrieval includes all line items."""
        client = db.add_client("Items Client")
        items = [("Design", 2500.0), ("Dev", 5000.0), ("QA", 1200.0)]
        inv = db.create_invoice(client.id, items)
        assert len(inv.items) == 3
        assert inv.items[0].description == "Design"
        assert inv.items[0].amount == 2500.0
        assert inv.items[1].description == "Dev"
        assert inv.items[2].description == "QA"

    def test_subtotal_is_sum_of_items(self):
        """Subtotal equals the sum of all line item amounts."""
        client = db.add_client("Sum Client")
        items = [("A", 100.50), ("B", 200.75), ("C", 50.25)]
        inv = db.create_invoice(client.id, items, tax_rate=0.0)
        assert inv.subtotal == pytest.approx(351.50, abs=0.01)
        assert inv.total == pytest.approx(351.50, abs=0.01)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SETTINGS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestSettings:
    def test_default_tax_rate(self):
        assert db.get_setting("tax_rate") == "0.0"

    def test_default_net_days(self):
        assert db.get_setting("net_days") == "30"

    def test_set_and_get(self):
        db.set_setting("tax_rate", "8.25")
        assert db.get_setting("tax_rate") == "8.25"

    def test_nonexistent_key_returns_empty(self):
        assert db.get_setting("nonexistent") == ""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# REVENUE QUERIES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestRevenueQueries:
    def _make_paid_invoice(self, name, amount):
        client = db.get_client_by_name(name)
        if not client:
            client = db.add_client(name)
        inv = db.create_invoice(client.id, [("Work", amount)])
        db.update_invoice_status(inv.id, InvoiceStatus.PAID.value)
        return inv

    def test_monthly_revenue_empty(self):
        assert db.get_monthly_revenue() == []

    def test_monthly_revenue_with_paid(self):
        self._make_paid_invoice("Rev Client", 1000.0)
        data = db.get_monthly_revenue()
        assert len(data) >= 1
        assert data[0]["revenue"] >= 1000.0

    def test_quarterly_revenue_empty(self):
        assert db.get_quarterly_revenue() == []

    def test_invoice_summary_all_zeros(self):
        summary = db.get_invoice_summary()
        assert summary["total_invoices"] == 0
        assert summary["total_billed"] == 0

    def test_invoice_summary_with_data(self):
        client = db.add_client("Summary Client")
        db.create_invoice(client.id, [("A", 500.0)])
        db.create_invoice(client.id, [("B", 300.0)])
        summary = db.get_invoice_summary()
        assert summary["total_invoices"] == 2
        assert summary["total_billed"] == 800.0
        assert summary["drafts"] == 2
