"""Tests for CLI commands using Typer's CliRunner."""

import pytest
from typer.testing import CliRunner

from invoicegen.cli import app
from invoicegen import database as db

runner = CliRunner()


class TestVersionCommand:
    def test_version_output(self):
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "1.0.0" in result.output


class TestClientCommands:
    def test_add_client(self):
        result = runner.invoke(
            app, ["client", "add", "--name", "Test Corp", "--email", "t@test.com"]
        )
        assert result.exit_code == 0
        assert "Test Corp" in result.output

    def test_add_duplicate_client(self):
        runner.invoke(app, ["client", "add", "--name", "Dupe Corp"])
        result = runner.invoke(app, ["client", "add", "--name", "Dupe Corp"])
        assert result.exit_code == 1

    def test_list_clients_empty(self):
        result = runner.invoke(app, ["client", "list"])
        assert result.exit_code == 0
        assert "No clients" in result.output

    def test_list_clients_with_data(self):
        runner.invoke(app, ["client", "add", "--name", "Listed Corp"])
        result = runner.invoke(app, ["client", "list"])
        assert result.exit_code == 0
        assert "Listed Corp" in result.output

    def test_remove_client(self):
        runner.invoke(app, ["client", "add", "--name", "Remove Me"])
        result = runner.invoke(app, ["client", "remove", "--name", "Remove Me"])
        assert result.exit_code == 0
        assert "removed" in result.output

    def test_remove_nonexistent_client(self):
        result = runner.invoke(app, ["client", "remove", "--name", "Ghost"])
        assert result.exit_code == 1


class TestInvoiceCommands:
    def _add_client(self):
        runner.invoke(
            app,
            ["client", "add", "--name", "Invoice Client", "--email", "ic@test.com"],
        )

    def test_create_invoice(self):
        self._add_client()
        result = runner.invoke(
            app,
            [
                "invoice", "create",
                "--client", "Invoice Client",
                "--items", "Web Design:2500,SEO:1500",
            ],
        )
        assert result.exit_code == 0
        assert "Invoice created" in result.output
        assert "4,000.00" in result.output

    def test_create_invoice_nonexistent_client(self):
        result = runner.invoke(
            app,
            ["invoice", "create", "--client", "Nobody", "--items", "Work:100"],
        )
        assert result.exit_code == 1

    def test_create_invoice_bad_items_format(self):
        self._add_client()
        result = runner.invoke(
            app,
            ["invoice", "create", "--client", "Invoice Client", "--items", "BadFormat"],
        )
        assert result.exit_code == 1

    def test_create_invoice_bad_amount(self):
        self._add_client()
        result = runner.invoke(
            app,
            [
                "invoice", "create",
                "--client", "Invoice Client",
                "--items", "Work:notanumber",
            ],
        )
        assert result.exit_code == 1

    def test_list_invoices_empty(self):
        result = runner.invoke(app, ["invoice", "list"])
        assert result.exit_code == 0
        assert "No invoices" in result.output

    def test_view_invoice(self):
        self._add_client()
        runner.invoke(
            app,
            [
                "invoice", "create",
                "--client", "Invoice Client",
                "--items", "Design:3000",
            ],
        )
        result = runner.invoke(app, ["invoice", "view", "1"])
        assert result.exit_code == 0
        assert "Invoice Client" in result.output
        assert "Design" in result.output

    def test_view_nonexistent_invoice(self):
        result = runner.invoke(app, ["invoice", "view", "999"])
        assert result.exit_code == 1

    def test_update_status(self):
        self._add_client()
        runner.invoke(
            app,
            [
                "invoice", "create",
                "--client", "Invoice Client",
                "--items", "Work:500",
            ],
        )
        result = runner.invoke(app, ["invoice", "status", "1", "--set", "sent"])
        assert result.exit_code == 0
        assert "Sent" in result.output

    def test_update_status_invalid(self):
        self._add_client()
        runner.invoke(
            app,
            [
                "invoice", "create",
                "--client", "Invoice Client",
                "--items", "Work:500",
            ],
        )
        result = runner.invoke(app, ["invoice", "status", "1", "--set", "invalid"])
        assert result.exit_code == 1

    def test_pdf_export(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        self._add_client()
        runner.invoke(
            app,
            [
                "invoice", "create",
                "--client", "Invoice Client",
                "--items", "Work:500",
            ],
        )
        out = tmp_path / "test_invoice.pdf"
        result = runner.invoke(
            app, ["invoice", "pdf", "1", "--output", str(out)]
        )
        assert result.exit_code == 0
        assert out.exists()

    def test_pdf_nonexistent_invoice(self):
        result = runner.invoke(app, ["invoice", "pdf", "999"])
        assert result.exit_code == 1


class TestConfigCommands:
    def test_show_config(self):
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "Tax Rate" in result.output

    def test_set_tax_rate(self):
        result = runner.invoke(app, ["config", "set", "--tax-rate", "8.25"])
        assert result.exit_code == 0
        assert "8.25" in result.output

    def test_set_net_days(self):
        result = runner.invoke(app, ["config", "set", "--net-days", "45"])
        assert result.exit_code == 0
        assert "45" in result.output

    def test_set_nothing(self):
        result = runner.invoke(app, ["config", "set"])
        assert result.exit_code == 0
        assert "No settings changed" in result.output

    def test_set_negative_tax_rate(self):
        result = runner.invoke(app, ["config", "set", "--tax-rate", "-5"])
        assert result.exit_code == 1

    def test_set_zero_net_days(self):
        result = runner.invoke(app, ["config", "set", "--net-days", "0"])
        assert result.exit_code == 1


class TestReportCommands:
    def test_monthly_report_empty(self):
        result = runner.invoke(app, ["report", "monthly"])
        assert result.exit_code == 0
        assert "No paid invoices" in result.output

    def test_quarterly_report_empty(self):
        result = runner.invoke(app, ["report", "quarterly"])
        assert result.exit_code == 0
        assert "No paid invoices" in result.output
