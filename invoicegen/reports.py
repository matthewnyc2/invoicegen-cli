"""Revenue reporting with Rich tables and Unicode charts -- Brutalist Command theme."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from invoicegen import database as db
from invoicegen.theme import (
    BRUTALIST_THEME,
    PRIMARY,
    PRIMARY_DIM,
    SECONDARY,
    TERTIARY,
    ERROR,
    MUTED,
    GHOST,
    WARNING,
    BLOCK_FULL,
    BLOCK_DARK,
    BLOCK_MED,
    BLOCK_LIGHT,
)

console = Console(theme=BRUTALIST_THEME)


def _gradient_bar(width: int, max_width: int = 28) -> Text:
    """Build a gradient bar using Unicode block elements.

    Gradient: primary_dim -> primary (left to right).
    Uses full/dark/medium blocks for the filled portion, light blocks for empty.
    """
    bar = Text()
    if width <= 0:
        bar.append(BLOCK_LIGHT * max_width, style=GHOST)
        return bar

    # Split the filled portion into gradient thirds
    third = max(1, width // 3)
    remainder = width - (third * 2)

    bar.append(BLOCK_MED * third, style=PRIMARY_DIM)
    bar.append(BLOCK_DARK * third, style=PRIMARY)
    bar.append(BLOCK_FULL * remainder, style=PRIMARY)

    empty = max_width - width
    if empty > 0:
        bar.append(BLOCK_LIGHT * empty, style=GHOST)

    return bar


def _gradient_bar_cyan(width: int, max_width: int = 28) -> Text:
    """Cyan variant for quarterly charts."""
    bar = Text()
    if width <= 0:
        bar.append(BLOCK_LIGHT * max_width, style=GHOST)
        return bar

    third = max(1, width // 3)
    remainder = width - (third * 2)

    bar.append(BLOCK_MED * third, style=MUTED)
    bar.append(BLOCK_DARK * third, style=SECONDARY)
    bar.append(BLOCK_FULL * remainder, style=SECONDARY)

    empty = max_width - width
    if empty > 0:
        bar.append(BLOCK_LIGHT * empty, style=GHOST)

    return bar


def monthly_report() -> None:
    """Display monthly revenue summary."""
    data = db.get_monthly_revenue()
    summary = db.get_invoice_summary()

    if not data:
        console.print(
            Panel(
                f"[warning]No paid invoices found.[/warning]\n"
                f"Create invoices and mark them as paid to see revenue reports.",
                title="[secondary]Monthly Revenue Report[/secondary]",
                border_style=GHOST,
            )
        )
        return

    _print_summary(summary)

    table = Table(
        title="[secondary]Monthly Revenue[/secondary]",
        show_header=True,
        header_style=f"bold {SECONDARY}",
        border_style=GHOST,
        padding=(0, 2),
        show_lines=False,
    )
    table.add_column("Month", style=f"bold {TERTIARY}")
    table.add_column("Invoices", justify="right", style=MUTED)
    table.add_column("Revenue", justify="right", style=PRIMARY)
    table.add_column("", min_width=30)

    max_rev = max(r["revenue"] for r in data) if data else 1

    for row in data:
        bar_width = int((row["revenue"] / max_rev) * 28) if max_rev > 0 else 0
        bar = _gradient_bar(bar_width)

        table.add_row(
            row["month"],
            str(row["invoice_count"]),
            f"${row['revenue']:,.2f}",
            bar,
        )

    console.print()
    console.print(table)


def quarterly_report() -> None:
    """Display quarterly revenue summary with Unicode chart."""
    data = db.get_quarterly_revenue()
    summary = db.get_invoice_summary()

    if not data:
        console.print(
            Panel(
                f"[warning]No paid invoices found.[/warning]\n"
                f"Create invoices and mark them as paid to see revenue reports.",
                title="[secondary]Quarterly Revenue Report[/secondary]",
                border_style=GHOST,
            )
        )
        return

    _print_summary(summary)

    table = Table(
        title="[secondary]Quarterly Revenue[/secondary]",
        show_header=True,
        header_style=f"bold {SECONDARY}",
        border_style=GHOST,
        padding=(0, 2),
        show_lines=False,
    )
    table.add_column("Quarter", style=f"bold {TERTIARY}")
    table.add_column("Invoices", justify="right", style=MUTED)
    table.add_column("Revenue", justify="right", style=PRIMARY)
    table.add_column("", min_width=30)

    max_rev = max(r["revenue"] for r in data) if data else 1

    for row in data:
        label = f"{row['year']} {row['quarter']}"
        bar_width = int((row["revenue"] / max_rev) * 28) if max_rev > 0 else 0
        bar = _gradient_bar_cyan(bar_width)

        table.add_row(
            label,
            str(row["invoice_count"]),
            f"${row['revenue']:,.2f}",
            bar,
        )

    console.print()
    console.print(table)

    console.print()
    _ascii_chart(data)


def _print_summary(summary: dict) -> None:
    """Print the invoice summary panel."""
    summary_text = (
        f"[data.label]Total Billed:[/data.label]      [primary]${summary['total_billed']:,.2f}[/primary]\n"
        f"[data.label]Collected:[/data.label]          [primary]${summary['total_collected']:,.2f}[/primary]\n"
        f"[data.label]Outstanding:[/data.label]        [warning]${summary['total_outstanding']:,.2f}[/warning]\n"
        f"\n"
        f"[muted]Invoices:[/muted] {summary['total_invoices']} total "
        f"[muted]|[/muted] {summary['drafts']} draft "
        f"[muted]|[/muted] {summary['sent']} sent "
        f"[muted]|[/muted] [primary]{summary['paid']} paid[/primary] "
        f"[muted]|[/muted] [error]{summary['overdue']} overdue[/error]"
    )
    console.print(
        Panel(
            summary_text,
            title="[secondary]Invoice Summary[/secondary]",
            border_style=GHOST,
        )
    )


def _ascii_chart(data: list[dict]) -> None:
    """Render a Unicode block bar chart for quarterly data."""
    if not data:
        return

    chart_height = 10
    max_rev = max(r["revenue"] for r in data) if data else 1

    # Chronological order (oldest left)
    chart_data = list(reversed(data))

    console.print(
        Panel.fit(
            f"[secondary]Quarterly Revenue Chart[/secondary]",
            border_style=GHOST,
        )
    )

    for row_idx in range(chart_height, 0, -1):
        threshold = (row_idx / chart_height) * max_rev
        line_parts = []

        if row_idx == chart_height:
            label = f"[{MUTED}]${max_rev:>10,.0f} \u2503[/{MUTED}]"
        elif row_idx == chart_height // 2:
            label = f"[{MUTED}]${max_rev / 2:>10,.0f} \u2503[/{MUTED}]"
        elif row_idx == 1:
            label = f"[{MUTED}]{'$0':>11s} \u2503[/{MUTED}]"
        else:
            label = f"[{MUTED}]{'':>11s} \u2503[/{MUTED}]"

        line_parts.append(label)

        for item in chart_data:
            if item["revenue"] >= threshold:
                line_parts.append(f"  [{SECONDARY}]{BLOCK_FULL * 4}[/{SECONDARY}]  ")
            else:
                line_parts.append("        ")

        console.print("".join(line_parts))

    # X-axis with box-drawing
    x_axis = f"[{MUTED}]{'':>11s} \u2517[/{MUTED}]" + f"[{MUTED}]{'━' * 8}[/{MUTED}]" * len(chart_data)
    console.print(x_axis)

    # Labels
    label_line = f"{'':>12s} "
    for item in chart_data:
        qlabel = f"{item['year'][-2:]}-{item['quarter']}"
        label_line += f"[{TERTIARY}] {qlabel:^6s} [/{TERTIARY}]"
    console.print(label_line)
