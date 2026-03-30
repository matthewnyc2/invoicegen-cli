"""SQLite database layer for InvoiceGen."""

import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from invoicegen.models import Client, Invoice, InvoiceStatus, LineItem

# Store DB in user's home directory so it persists across installs
DB_DIR = Path.home() / ".invoicegen"
DB_PATH = DB_DIR / "invoicegen.db"


def get_db_path() -> Path:
    """Return the database path, creating the directory if needed."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    return DB_PATH


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory."""
    conn = sqlite3.connect(str(get_db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Initialize the database schema."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL DEFAULT '',
            address TEXT NOT NULL DEFAULT '',
            phone TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT NOT NULL UNIQUE,
            client_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Draft',
            subtotal REAL NOT NULL DEFAULT 0,
            tax_rate REAL NOT NULL DEFAULT 0,
            tax_amount REAL NOT NULL DEFAULT 0,
            total REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (date('now')),
            due_date TEXT NOT NULL,
            paid_at TEXT,
            notes TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );

        CREATE TABLE IF NOT EXISTS line_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)

    # Insert default settings if not present
    cursor.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
        ("tax_rate", "0.0"),
    )
    cursor.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
        ("net_days", "30"),
    )

    conn.commit()
    conn.close()


# --- Settings ---

def get_setting(key: str) -> str:
    """Get a setting value by key."""
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else ""


def set_setting(key: str, value: str) -> None:
    """Set a setting value."""
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value)
    )
    conn.commit()
    conn.close()


# --- Clients ---

def add_client(name: str, email: str = "", address: str = "", phone: str = "") -> Client:
    """Add a new client."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO clients (name, email, address, phone) VALUES (?, ?, ?, ?)",
        (name, email, address, phone),
    )
    conn.commit()
    client_id = cursor.lastrowid
    conn.close()
    return Client(id=client_id, name=name, email=email, address=address, phone=phone)


def get_client_by_name(name: str) -> Optional[Client]:
    """Find a client by exact name."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM clients WHERE name = ?", (name,)).fetchone()
    conn.close()
    if row:
        return Client(**dict(row))
    return None


def list_clients() -> list[Client]:
    """List all clients."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM clients ORDER BY name").fetchall()
    conn.close()
    return [Client(**dict(r)) for r in rows]


def delete_client(client_id: int) -> bool:
    """Delete a client by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM clients WHERE id = ?", (client_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


# --- Invoices ---

def _next_invoice_number() -> str:
    """Generate the next invoice number in format INV-YYYY-NNNN."""
    year = date.today().year
    conn = get_connection()
    row = conn.execute(
        "SELECT invoice_number FROM invoices WHERE invoice_number LIKE ? ORDER BY invoice_number DESC LIMIT 1",
        (f"INV-{year}-%",),
    ).fetchone()
    conn.close()

    if row:
        last_num = int(row["invoice_number"].split("-")[-1])
        return f"INV-{year}-{last_num + 1:04d}"
    return f"INV-{year}-0001"


def create_invoice(
    client_id: int,
    items: list[tuple[str, float]],
    tax_rate: Optional[float] = None,
    net_days: Optional[int] = None,
    notes: str = "",
) -> Invoice:
    """Create a new invoice with line items."""
    if tax_rate is None:
        tax_rate = float(get_setting("tax_rate"))
    if net_days is None:
        net_days = int(get_setting("net_days"))

    invoice_number = _next_invoice_number()
    subtotal = sum(amount for _, amount in items)
    tax_amount = round(subtotal * tax_rate / 100, 2)
    total = round(subtotal + tax_amount, 2)
    created_at = date.today().isoformat()
    due_date = (date.today() + timedelta(days=net_days)).isoformat()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """INSERT INTO invoices
           (invoice_number, client_id, status, subtotal, tax_rate, tax_amount, total, created_at, due_date, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            invoice_number,
            client_id,
            InvoiceStatus.DRAFT.value,
            subtotal,
            tax_rate,
            tax_amount,
            total,
            created_at,
            due_date,
            notes,
        ),
    )
    invoice_id = cursor.lastrowid

    for desc, amount in items:
        cursor.execute(
            "INSERT INTO line_items (invoice_id, description, amount) VALUES (?, ?, ?)",
            (invoice_id, desc, amount),
        )

    conn.commit()
    conn.close()

    return get_invoice(invoice_id)


def get_invoice(invoice_id: int) -> Optional[Invoice]:
    """Get an invoice by ID, including client info and line items."""
    conn = get_connection()
    row = conn.execute(
        """SELECT i.*, c.name as client_name, c.email as client_email, c.address as client_address
           FROM invoices i
           JOIN clients c ON i.client_id = c.id
           WHERE i.id = ?""",
        (invoice_id,),
    ).fetchone()

    if not row:
        conn.close()
        return None

    items_rows = conn.execute(
        "SELECT * FROM line_items WHERE invoice_id = ? ORDER BY id", (invoice_id,)
    ).fetchall()
    conn.close()

    inv = Invoice(
        id=row["id"],
        invoice_number=row["invoice_number"],
        client_id=row["client_id"],
        client_name=row["client_name"],
        client_email=row["client_email"],
        client_address=row["client_address"],
        status=row["status"],
        subtotal=row["subtotal"],
        tax_rate=row["tax_rate"],
        tax_amount=row["tax_amount"],
        total=row["total"],
        created_at=row["created_at"],
        due_date=row["due_date"],
        paid_at=row["paid_at"],
        notes=row["notes"],
        items=[LineItem(**dict(r)) for r in items_rows],
    )
    return inv


def list_invoices() -> list[Invoice]:
    """List all invoices with client info."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT i.*, c.name as client_name, c.email as client_email, c.address as client_address
           FROM invoices i
           JOIN clients c ON i.client_id = c.id
           ORDER BY i.id DESC"""
    ).fetchall()
    conn.close()

    invoices = []
    for row in rows:
        inv = Invoice(
            id=row["id"],
            invoice_number=row["invoice_number"],
            client_id=row["client_id"],
            client_name=row["client_name"],
            client_email=row["client_email"],
            client_address=row["client_address"],
            status=row["status"],
            subtotal=row["subtotal"],
            tax_rate=row["tax_rate"],
            tax_amount=row["tax_amount"],
            total=row["total"],
            created_at=row["created_at"],
            due_date=row["due_date"],
            paid_at=row["paid_at"],
            notes=row["notes"] if row["notes"] else "",
        )
        invoices.append(inv)
    return invoices


def update_invoice_status(invoice_id: int, status: str) -> bool:
    """Update invoice status. Sets paid_at when marking as Paid."""
    conn = get_connection()
    cursor = conn.cursor()

    if status == InvoiceStatus.PAID.value:
        cursor.execute(
            "UPDATE invoices SET status = ?, paid_at = ? WHERE id = ?",
            (status, datetime.now().isoformat(), invoice_id),
        )
    else:
        cursor.execute(
            "UPDATE invoices SET status = ?, paid_at = NULL WHERE id = ?",
            (status, invoice_id),
        )

    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated


def get_monthly_revenue() -> list[dict]:
    """Get revenue grouped by month (based on paid_at date)."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT
             strftime('%Y-%m', paid_at) as month,
             COUNT(*) as invoice_count,
             SUM(total) as revenue
           FROM invoices
           WHERE status = 'Paid' AND paid_at IS NOT NULL
           GROUP BY strftime('%Y-%m', paid_at)
           ORDER BY month DESC
           LIMIT 12"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_quarterly_revenue() -> list[dict]:
    """Get revenue grouped by quarter."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT
             strftime('%Y', paid_at) as year,
             CASE
               WHEN CAST(strftime('%m', paid_at) AS INTEGER) BETWEEN 1 AND 3 THEN 'Q1'
               WHEN CAST(strftime('%m', paid_at) AS INTEGER) BETWEEN 4 AND 6 THEN 'Q2'
               WHEN CAST(strftime('%m', paid_at) AS INTEGER) BETWEEN 7 AND 9 THEN 'Q3'
               ELSE 'Q4'
             END as quarter,
             COUNT(*) as invoice_count,
             SUM(total) as revenue
           FROM invoices
           WHERE status = 'Paid' AND paid_at IS NOT NULL
           GROUP BY year, quarter
           ORDER BY year DESC, quarter DESC
           LIMIT 8"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_invoice_summary() -> dict:
    """Get a summary of all invoices."""
    conn = get_connection()
    row = conn.execute(
        """SELECT
             COUNT(*) as total_invoices,
             SUM(CASE WHEN status = 'Draft' THEN 1 ELSE 0 END) as drafts,
             SUM(CASE WHEN status = 'Sent' THEN 1 ELSE 0 END) as sent,
             SUM(CASE WHEN status = 'Paid' THEN 1 ELSE 0 END) as paid,
             SUM(CASE WHEN status != 'Paid' AND due_date < date('now') THEN 1 ELSE 0 END) as overdue,
             COALESCE(SUM(total), 0) as total_billed,
             COALESCE(SUM(CASE WHEN status = 'Paid' THEN total ELSE 0 END), 0) as total_collected,
             COALESCE(SUM(CASE WHEN status != 'Paid' THEN total ELSE 0 END), 0) as total_outstanding
           FROM invoices"""
    ).fetchone()
    conn.close()
    return dict(row)
