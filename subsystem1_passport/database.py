"""SQLite database with Python's built-in sqlite3 module (same approach as Rajib's db.py).

Tables: users, products, material_components, qr_codes, and the append-only history_events.
Triggers make NFR 7 hold in the database itself: products and history rows cannot be deleted,
history rows cannot be changed, and a product's UUID cannot be changed.
"""
import os
import sqlite3
from contextlib import contextmanager

DEFAULT_PATH = "passport.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT NOT NULL UNIQUE,
    role          TEXT NOT NULL CHECK (role IN ('admin', 'manufacturer', 'recycler', 'consumer')),
    password_hash TEXT NOT NULL,
    active        INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid                TEXT NOT NULL UNIQUE,
    name                TEXT NOT NULL,
    model               TEXT NOT NULL DEFAULT '',
    category            TEXT NOT NULL,
    lifespan_years      REAL NOT NULL,
    spare_parts_percent REAL,
    owner_id            INTEGER REFERENCES users(id),
    archived            INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_owner ON products(owner_id);

CREATE TABLE IF NOT EXISTS material_components (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id     INTEGER NOT NULL REFERENCES products(id),
    material       TEXT NOT NULL,
    percent        REAL NOT NULL,
    recycled_share REAL NOT NULL DEFAULT 0,
    recyclable     INTEGER NOT NULL DEFAULT 1,
    hazard         INTEGER NOT NULL DEFAULT 0,
    active         INTEGER NOT NULL DEFAULT 1   -- edited materials are switched off, not deleted
);
CREATE INDEX IF NOT EXISTS idx_materials_product ON material_components(product_id);

CREATE TABLE IF NOT EXISTS qr_codes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL UNIQUE REFERENCES products(id),
    target_url TEXT NOT NULL,
    png_bytes  BLOB NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS history_events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id    INTEGER NOT NULL REFERENCES products(id),
    event_type    TEXT NOT NULL,
    timestamp     TEXT NOT NULL,
    actor_email   TEXT NOT NULL,
    actor_role    TEXT NOT NULL,
    details       TEXT NOT NULL DEFAULT '',
    previous_hash TEXT NOT NULL,
    event_hash    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_history_product ON history_events(product_id);

-- NFR 7: no hard deletes, UUIDs never change, history is append-only.
CREATE TRIGGER IF NOT EXISTS products_no_delete BEFORE DELETE ON products
BEGIN SELECT RAISE(ABORT, 'Products are never deleted, archive them instead.'); END;
CREATE TRIGGER IF NOT EXISTS products_uuid_fixed BEFORE UPDATE OF uuid ON products
BEGIN SELECT RAISE(ABORT, 'A product UUID cannot be changed.'); END;
CREATE TRIGGER IF NOT EXISTS history_no_delete BEFORE DELETE ON history_events
BEGIN SELECT RAISE(ABORT, 'History entries are never deleted.'); END;
CREATE TRIGGER IF NOT EXISTS history_no_update BEFORE UPDATE ON history_events
BEGIN SELECT RAISE(ABORT, 'History entries are never changed.'); END;
"""


def connect(path):
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if path != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")  # readers do not wait for writers
    return conn


class Database:
    """Opens one connection per request. ':memory:' (tests) shares a single connection."""

    def __init__(self, path=None):
        self.path = path or os.environ.get("DATABASE_PATH", DEFAULT_PATH)
        self._shared = connect(self.path) if self.path == ":memory:" else None
        with self.connection() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connection(self):
        conn = self._shared or connect(self.path)
        try:
            yield conn
        finally:
            if conn.in_transaction:  # anything not committed is discarded
                conn.rollback()
            if conn is not self._shared:
                conn.close()

    def close(self):
        if self._shared is not None:
            self._shared.close()
            self._shared = None
