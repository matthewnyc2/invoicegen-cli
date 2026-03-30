"""Shared fixtures for InvoiceGen tests.

Every test gets a fresh in-memory SQLite database so tests never
collide with the real user DB or with each other.
"""

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from invoicegen import database as db


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    """Redirect database to a temp file for every test."""
    test_db = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", test_db)
    db.init_db()
    yield
