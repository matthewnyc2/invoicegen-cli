"""CLI interface for InvoiceGen using Typer and Rich — Brutalist Command theme."""

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from invoicegen import __version__, database as db
from invoicegen.models import InvoiceStatus
from invoicegen.pdf_generator import generate_pdf
from invoicegen.reports import monthly_report, quarterly_report
from invoicegen.theme import (
    BRUTALIST_THEME,
    PRIMARY,
    SECONDARY,
    TERTIARY,
    ERROR,
    MUTED,
    GHOST,
    BLOCK_FULL,
    BLOCK_LIGHT,
)

console = Console(theme=BRUTALIST_THEME)

# ── App and sub-commands ───────────────────────────────────────
app = typer.Typer(
    name="invoicegen",
    help="Professional CLI invoice generator with PDF export and revenue reporting.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

client_app = typer.Typer(help="Manage clients.", no_args_is_help=True)
invoice_app = typer.Typer(help="Create and manage invoices.", no_args_is_help=True)
report_app = typer.Typer(help="Revenue reports and analytics.", no_args_is_help=True)
config_app = typer.Typer(help="Configure InvoiceGen settings.", no_args_is_help=True)

app.add_typer(client_app, name="client")
app.add_typer(invoice_app, name="invoice")
app.add_typer(report_app, name="report")
app.add_typer(config_app, name="config")


@app.callback()
def main_callback():
    """InvoiceGen - Professional CLI Invoice Generator."""
    db.init_db()


# ── Version ────────────────────────────────────────────────────
@app.command()
def version():
    """Show the InvoiceGen version."""
    console.print(
        f"[secondary]invoicegen[/secondary] [{PRIMARY}]v{__version__}[/{PRIMARY}]"
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLIENT COMMANDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@client_app.command("add")
def client_add(
    name: str = typer.Option(..., "--name", "-n", help="Client name"),
    email: str = typer.Option("", "--email", "-e", help="Client email"),
    address: str = typer.Option("", "--address", "-a", help="Client address"),
    phone: str = typer.Option("", "--phone", "-p", help="Client phone number"),
):
    """Add a new client."""
    existing = db.get_client_by_name(name)
    if existing:
        console.print(f"[error]Error:[/error] Client '{name}' already exists.")
        raise typer.Exit(1)

    client = db.add_client(name=name, email=email, address=address, phone=phone)
    console.print(
        Panel(
            f"[primary]Client added[/primary]\n\n"
            f"  [data.label]Name:[/data.label]    {client.name}\n"
            f"  [data.label]Email:[/data.label]   {client.email or '\u2014'}\n"
            f"  [data.label]Address:[/data.label] {client.address or '\u2014'}\n"
            f"  [data.label]Phone:[/data.label]   {client.phone or '\u2014'}",
            title="[secondary]New Client[/secondary]",
            border_style=GHOST,
        )
    )


@client_app.command("list")
def client_list():
    """List all clients in a table."""
    clients = db.list_clients()

    if not clients:
        console.print(
            f"[warning]No clients found.[/warning] "
            f"Add one with: [{PRIMARY}]invoicegen client add --name \"...\"[/{PRIMARY}]"
        )
        return

    table = Table(
        title="[secondary]Clients[/secondary]",
        show_header=True,
        header_style=f"bold {SECONDARY}",
        border_style=GHOST,
        padding=(0, 2),
        show_lines=False,
    )
    table.add_column("ID", justify="right", style=MUTED)
    table.add_column("Name", style=f"bold {PRIMARY}")
    table.add_column("Email", style=TERTIARY)
    table.add_column("Address")
    table.add_column("Phone")

    for c in clients:
        table.add_row(
            str(c.id),
            c.name,
            c.email or "\u2014",
            c.address or "\u2014",
            c.phone or "\u2014",
        )

    console.print(table)


@client_app.command("remove")
def client_remove(
    name: str = typer.Option(..., "--name", "-n", help="Client name to remove"),
):
    """Remove a client by name."""
    client = db.get_client_by_name(name)
    if not client:
        console.print(f"[error]Error:[/error] Client '{name}' not found.")
        raise typer.Exit(1)

    db.delete_client(client.id)
    console.print(f"[primary]Client '{name}' removed.[/primary]")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INVOICE COMMANDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@invoice_app.command("create")
def invoice_create(
    client: str = typer.Option(..., "--client", "-c", help="Client name"),
    items: str = typer.Option(
        ..., "--items", "-i",
        help='Line items as "Description:Amount,..." e.g. "Web Design:2500,SEO:1500"',
    ),
    tax: Optional[float] = typer.Option(
        None, "--tax", "-t", help="Tax rate percentage (overrides default)"
    ),
    net_days: Optional[int] = typer.Option(
        None, "--net", help="Payment terms in days (overrides default)"
    ),
    notes: str = typer.Option("", "--notes", help="Additional notes"),
):
    """Create a new invoice for a client."""
    client_obj = db.get_client_by_name(client)
    if not client_obj:
        console.print(
            f"[error]Error:[/error] Client '{client}' not found. "
            f"Add them first with: [{PRIMARY}]invoicegen client add --name \"{client}\"[/{PRIMARY}]"
        )
        raise typer.Exit(1)

    parsed_items = []
    try:
        for item_str in items.split(","):
            item_str = item_str.strip()
            if ":" not in item_str:
                console.print(
                    f"[error]Error:[/error] Invalid item format: '{item_str}'. "
                    f"Use 'Description:Amount'"
                )
                raise typer.Exit(1)
            desc, amount_str = item_str.rsplit(":", 1)
            parsed_items.append((desc.strip(), float(amount_str.strip())))
    except ValueError:
        console.print(
            "[error]Error:[/error] Could not parse item amounts. "
            "Ensure amounts are numbers."
        )
        raise typer.Exit(1)

    if not parsed_items:
        console.print("[error]Error:[/error] At least one line item is required.")
        raise typer.Exit(1)

    invoice = db.create_invoice(
        client_id=client_obj.id,
        items=parsed_items,
        tax_rate=tax,
        net_days=net_days,
        notes=notes,
    )

    console.print(
        Panel(
            f"[primary]Invoice created[/primary]\n\n"
            f"  [data.label]Invoice #:[/data.label]  {invoice.invoice_number}\n"
            f"  [data.label]Client:[/data.label]     {invoice.client_name}\n"
            f"  [data.label]Items:[/data.label]      {len(invoice.items)}\n"
            f"  [data.label]Subtotal:[/data.label]   [data.money]${invoice.subtotal:,.2f}[/data.money]\n"
            f"  [data.label]Tax:[/data.label]        [data.money]${invoice.tax_amount:,.2f}[/data.money] ({invoice.tax_rate}%)\n"
            f"  [data.label]Total:[/data.label]      [primary]${invoice.total:,.2f}[/primary]\n"
            f"  [data.label]Due Date:[/data.label]   {invoice.due_date}\n"
            f"  [data.label]Status:[/data.label]     {invoice.status}",
            title=f"[secondary]Invoice {invoice.invoice_number}[/secondary]",
            border_style=GHOST,
        )
    )


@invoice_app.command("list")
def invoice_list():
    """List all invoices."""
    invoices = db.list_invoices()

    if not invoices:
        console.print(
            f"[warning]No invoices found.[/warning] "
            f"Create one with: [{PRIMARY}]invoicegen invoice create --client \"...\" --items \"...\"[/{PRIMARY}]"
        )
        return

    table = Table(
        title="[secondary]Invoices[/secondary]",
        show_header=True,
        header_style=f"bold {SECONDARY}",
        border_style=GHOST,
        padding=(0, 1),
        show_lines=False,
    )
    table.add_column("ID", justify="right", style=MUTED)
    table.add_column("Invoice #", style=f"bold {PRIMARY}")
    table.add_column("Client")
    table.add_column("Total", justify="right", style=PRIMARY)
    table.add_column("Status", justify="center")
    table.add_column("Created", style=MUTED)
    table.add_column("Due Date")

    for inv in invoices:
        status = inv.effective_status
        if status == "Paid":
            status_display = Text("Paid", style=f"bold {PRIMARY}")
        elif status == "Overdue":
            status_display = Text("Overdue", style=f"bold {ERROR}")
        elif status == "Sent":
            status_display = Text("Sent", style=f"bold {TERTIARY}")
        else:
            status_display = Text("Draft", style=MUTED)

        due_style = f"bold {ERROR}" if inv.is_overdue else ""

        table.add_row(
            str(inv.id),
            inv.invoice_number,
            inv.client_name,
            f"${inv.total:,.2f}",
            status_display,
            inv.created_at,
            Text(inv.due_date, style=due_style),
        )

    console.print(table)


@invoice_app.command("view")
def invoice_view(
    invoice_id: int = typer.Argument(help="Invoice ID to view"),
):
    """View a formatted invoice in the terminal."""
    invoice = db.get_invoice(invoice_id)
    if not invoice:
        console.print(f"[error]Error:[/error] Invoice #{invoice_id} not found.")
        raise typer.Exit(1)

    status = invoice.effective_status
    status_style = {
        "Paid": f"bold {PRIMARY}",
        "Overdue": f"bold {ERROR}",
        "Sent": f"bold {TERTIARY}",
    }.get(status, MUTED)

    # Header
    header = (
        f"[primary]{invoice.invoice_number}[/primary]"
        f"                        "
        f"Status: [{status_style}]{status}[/{status_style}]\n"
        f"\n"
        f"[data.label]Bill To:[/data.label]\n"
        f"  {invoice.client_name}\n"
    )
    if invoice.client_email:
        header += f"  [{TERTIARY}]{invoice.client_email}[/{TERTIARY}]\n"
    if invoice.client_address:
        header += f"  {invoice.client_address}\n"

    header += (
        f"\n"
        f"[data.label]Date:[/data.label]     {invoice.created_at}\n"
        f"[data.label]Due Date:[/data.label] {invoice.due_date}"
    )

    console.print(
        Panel(header, title="[secondary]Invoice Details[/secondary]", border_style=GHOST)
    )

    # Line items table
    items_table = Table(
        show_header=True,
        header_style=f"bold {SECONDARY}",
        border_style=GHOST,
        padding=(0, 2),
        expand=True,
        show_lines=False,
    )
    items_table.add_column("#", justify="right", style=MUTED, width=4)
    items_table.add_column("Description")
    items_table.add_column("Amount", justify="right", style=PRIMARY)

    for idx, item in enumerate(invoice.items, 1):
        items_table.add_row(str(idx), item.description, f"${item.amount:,.2f}")

    console.print(items_table)

    # Totals
    totals = f"  [data.label]Subtotal:[/data.label]   [data.money]${invoice.subtotal:>12,.2f}[/data.money]\n"
    if invoice.tax_rate > 0:
        totals += f"  [data.label]Tax ({invoice.tax_rate}%):[/data.label]  [data.money]${invoice.tax_amount:>12,.2f}[/data.money]\n"
    totals += f"  [primary]Total:[/primary]      [primary]${invoice.total:>12,.2f}[/primary]"

    if invoice.notes:
        totals += f"\n\n  [muted]Notes: {invoice.notes}[/muted]"

    console.print(Panel(totals, border_style=GHOST))


@invoice_app.command("pdf")
def invoice_pdf(
    invoice_id: int = typer.Argument(help="Invoice ID to export"),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output PDF path"
    ),
):
    """Export an invoice to PDF."""
    invoice = db.get_invoice(invoice_id)
    if not invoice:
        console.print(f"[error]Error:[/error] Invoice #{invoice_id} not found.")
        raise typer.Exit(1)

    path = generate_pdf(invoice, output)
    console.print(
        Panel(
            f"[primary]PDF generated[/primary]\n\n"
            f"  [data.label]File:[/data.label]    {path.absolute()}\n"
            f"  [data.label]Invoice:[/data.label] {invoice.invoice_number}\n"
            f"  [data.label]Client:[/data.label]  {invoice.client_name}\n"
            f"  [data.label]Total:[/data.label]   [primary]${invoice.total:,.2f}[/primary]",
            title="[secondary]PDF Export[/secondary]",
            border_style=GHOST,
        )
    )


@invoice_app.command("status")
def invoice_status(
    invoice_id: int = typer.Argument(help="Invoice ID"),
    set_status: str = typer.Option(
        ..., "--set", "-s",
        help="New status: draft, sent, paid, overdue",
    ),
):
    """Update the status of an invoice."""
    status_map = {
        "draft": InvoiceStatus.DRAFT.value,
        "sent": InvoiceStatus.SENT.value,
        "paid": InvoiceStatus.PAID.value,
        "overdue": InvoiceStatus.OVERDUE.value,
    }

    normalized = status_map.get(set_status.lower())
    if not normalized:
        console.print(
            f"[error]Error:[/error] Invalid status '{set_status}'. "
            f"Choose from: draft, sent, paid, overdue"
        )
        raise typer.Exit(1)

    if not db.update_invoice_status(invoice_id, normalized):
        console.print(f"[error]Error:[/error] Invoice #{invoice_id} not found.")
        raise typer.Exit(1)

    style_map = {
        "Draft": MUTED,
        "Sent": TERTIARY,
        "Paid": PRIMARY,
        "Overdue": ERROR,
    }
    style = style_map.get(normalized, "")

    console.print(
        f"[{PRIMARY}]>[/{PRIMARY}] Invoice #{invoice_id} status "
        f"[{style}]{normalized}[/{style}]"
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# REPORT COMMANDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@report_app.command("monthly")
def report_monthly():
    """Monthly revenue summary with bar chart."""
    monthly_report()


@report_app.command("quarterly")
def report_quarterly():
    """Quarterly revenue summary with bar chart."""
    quarterly_report()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONFIG COMMANDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@config_app.command("show")
def config_show():
    """Show current configuration."""
    tax_rate = db.get_setting("tax_rate")
    net_days = db.get_setting("net_days")

    console.print(
        Panel(
            f"  [data.label]Tax Rate:[/data.label]      {tax_rate}%\n"
            f"  [data.label]Net Days:[/data.label]      {net_days} days\n"
            f"  [data.label]Database:[/data.label]      {db.get_db_path()}",
            title="[secondary]Configuration[/secondary]",
            border_style=GHOST,
        )
    )


@config_app.command("set")
def config_set(
    tax_rate: Optional[float] = typer.Option(
        None, "--tax-rate", help="Default tax rate percentage"
    ),
    net_days: Optional[int] = typer.Option(
        None, "--net-days", help="Default payment terms (days)"
    ),
):
    """Update configuration settings."""
    updated = False

    if tax_rate is not None:
        if tax_rate < 0:
            console.print("[error]Error:[/error] Tax rate cannot be negative.")
            raise typer.Exit(1)
        db.set_setting("tax_rate", str(tax_rate))
        console.print(f"[primary]Tax rate set to {tax_rate}%[/primary]")
        updated = True

    if net_days is not None:
        if net_days < 1:
            console.print("[error]Error:[/error] Net days must be at least 1.")
            raise typer.Exit(1)
        db.set_setting("net_days", str(net_days))
        console.print(f"[primary]Payment terms set to Net {net_days} days[/primary]")
        updated = True

    if not updated:
        console.print(
            "[warning]No settings changed.[/warning] Use --tax-rate or --net-days."
        )
