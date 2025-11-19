"""
db.py
-----------

This module provides basic database initialization and connection helpers for the
LinkedIn messaging CLI tool. All persistent data is stored in a SQLite
database on disk. The schema defines tables for account groups, accounts,
lead groups, leads, message logs and configuration data used by other
components of the application.  When the application starts it will call
``init_db`` to ensure all required tables exist.
"""

"""Database helpers and schema definition for the LinkedIn CLI."""

import sqlite3
from typing import Dict, Iterable


def init_db(db_path: str) -> None:
    """Create database tables if they do not already exist.

    Parameters
    ----------
    db_path: str
        Absolute or relative path to the SQLite database file.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Table of account groups (aliases) to group multiple LinkedIn accounts.
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS account_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
        """
    )

    # Table of LinkedIn accounts.
    # ``status`` can be 'viva', 'inestable' or 'muerta'.
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            alias TEXT,
            password TEXT,
            proxy TEXT,
            status TEXT NOT NULL DEFAULT 'viva',
            session_data TEXT,
            last_activity TEXT,
            last_message_at TEXT,
            last_error TEXT,
            cooldown_until TEXT,
            FOREIGN KEY(group_id) REFERENCES account_groups(id)
        )
        """
    )

    _ensure_account_columns(cur)

    # Table of lead groups. A lead group holds a collection of leads (profiles) to
    # contact. The same lead may exist in multiple groups if necessary.
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS lead_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
        """
    )

    # Table of leads. Each lead is associated with a group.
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            first_name TEXT,
            last_name TEXT,
            profile_url TEXT NOT NULL,
            note TEXT,
            FOREIGN KEY(group_id) REFERENCES lead_groups(id)
        )
        """
    )

    # Table of message logs. This table records a log of messages sent by the
    # tool. It does not store the full message content (to avoid storing
    # sensitive data) but logs the outcome.
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS message_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            account_id INTEGER NOT NULL,
            lead_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            error_message TEXT,
            FOREIGN KEY(account_id) REFERENCES accounts(id),
            FOREIGN KEY(lead_id) REFERENCES leads(id)
        )
        """
    )

    # Configuration table for storing arbitrary key/value pairs such as API
    # tokens and prompts for the autoresponder. Values are stored as text.
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )

    conn.commit()
    conn.close()


def get_connection(db_path: str) -> sqlite3.Connection:
    """Return a new SQLite connection with row factory set to Row.

    This helper is used by other modules to interact with the database.

    Parameters
    ----------
    db_path: str
        Path to the SQLite database file.

    Returns
    -------
    sqlite3.Connection
        A connection object configured with row factory to access columns by
        name.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_account_columns(cur: sqlite3.Cursor) -> None:
    """Ensure newer optional account columns exist (idempotent)."""

    existing = _table_columns(cur, "accounts")
    columns: Dict[str, str] = {
        "alias": "TEXT",
        "proxy": "TEXT",
        "last_activity": "TEXT",
        "last_message_at": "TEXT",
        "last_error": "TEXT",
        "cooldown_until": "TEXT",
    }
    for name, definition in columns.items():
        if name not in existing:
            cur.execute(f"ALTER TABLE accounts ADD COLUMN {name} {definition}")

    if "message_templates" not in _tables(cur):
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS message_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                content TEXT NOT NULL
            )
            """
        )


def _table_columns(cur: sqlite3.Cursor, table: str) -> Iterable[str]:
    cur.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]


def _tables(cur: sqlite3.Cursor) -> Iterable[str]:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [row[0] for row in cur.fetchall()]
