"""Tests for PDF generation -- file creation, content structure."""

from pathlib import Path

import pytest

from invoicegen.models import Invoice, LineItem
from invoicegen.pdf_generator import generate_pdf, _days_until_due


@pytest.fixture
def sample_invoice():
    """A fully populated Invoice for PDF tests."""
    return Invoice(
        id=1,
        invoice_number="INV-2026-0001",
        client_id=1,
        client_name="Acme Corp",
        client_email="billing@acme.com",
        client_address="123 Main St, Springfield, IL",
        status="Sent",
        subtotal=5000.0,
        tax_rate=8.5,
        tax_amount=425.0,
        total=5425.0,
        created_at="2026-03-01",
        due_date="2026-03-31",
        notes="Phase 1 of 3.",
        items=[
            LineItem(id=1, invoice_id=1, description="Web Design", amount=2500.0),
            LineItem(id=2, invoice_id=1, description="SEO Audit", amount=1500.0),
            LineItem(id=3, invoice_id=1, description="Hosting Setup", amount=1000.0),
        ],
    )


class TestPDFGeneration:
    def test_generates_pdf_file(self, sample_invoice, tmp_path):
        """PDF file is created at the specified path."""
        out = tmp_path / "test.pdf"
        result = generate_pdf(sample_invoice, str(out))
        assert result.exists()
        assert result.suffix == ".pdf"

    def test_pdf_is_nonempty(self, sample_invoice, tmp_path):
        """Generated PDF has actual content (not zero bytes)."""
        out = tmp_path / "test.pdf"
        generate_pdf(sample_invoice, str(out))
        assert out.stat().st_size > 500  # A real PDF is at least a few KB

    def test_default_filename(self, sample_invoice, tmp_path, monkeypatch):
        """Without output_path, uses invoice_number.pdf."""
        monkeypatch.chdir(tmp_path)
        result = generate_pdf(sample_invoice)
        assert result.name == "INV-2026-0001.pdf"

    def test_pdf_with_zero_tax(self, tmp_path):
        """PDF generates correctly with 0% tax."""
        inv = Invoice(
            id=2,
            invoice_number="INV-2026-0002",
            client_name="No Tax Corp",
            subtotal=1000.0,
            tax_rate=0.0,
            tax_amount=0.0,
            total=1000.0,
            created_at="2026-03-15",
            due_date="2026-04-14",
            items=[LineItem(description="Consulting", amount=1000.0)],
        )
        out = tmp_path / "notax.pdf"
        result = generate_pdf(inv, str(out))
        assert result.exists()

    def test_pdf_with_no_notes(self, tmp_path):
        """PDF generates correctly without notes."""
        inv = Invoice(
            id=3,
            invoice_number="INV-2026-0003",
            client_name="Brief Client",
            subtotal=500.0,
            tax_rate=5.0,
            tax_amount=25.0,
            total=525.0,
            created_at="2026-01-01",
            due_date="2026-01-31",
            notes="",
            items=[LineItem(description="Quick Job", amount=500.0)],
        )
        out = tmp_path / "nonotes.pdf"
        result = generate_pdf(inv, str(out))
        assert result.exists()


class TestDaysUntilDue:
    def test_30_day_terms(self):
        inv = Invoice(created_at="2026-03-01", due_date="2026-03-31")
        assert _days_until_due(inv) == 30

    def test_45_day_terms(self):
        inv = Invoice(created_at="2026-01-01", due_date="2026-02-15")
        assert _days_until_due(inv) == 45

    def test_invalid_dates_returns_30(self):
        inv = Invoice(created_at="bad", due_date="also-bad")
        assert _days_until_due(inv) == 30

    def test_none_dates_returns_30(self):
        inv = Invoice(created_at=None, due_date=None)
        assert _days_until_due(inv) == 30
