"""Opens the shared SQLite database and creates its tables from schema.sql."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

FOLDER = Path(__file__).parent
SCHEMA_PATH = FOLDER / "schema.sql"


def db_path():
    """The database file. Set PASSPORT_DB to use another file, for example in a test."""
    return Path(os.environ.get("PASSPORT_DB", FOLDER / "passport.db"))


@contextmanager
def connect():
    """One connection and one transaction: `with connect() as conn:`.
    Everything inside commits together, or nothing is saved if an error happens."""
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row  # rows can be read by column name
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create every table that does not exist yet."""
    with connect() as conn:
        conn.executescript(SCHEMA_PATH.read_text())


def table_names():
    with connect() as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' "
                            "AND name NOT LIKE 'sqlite_%' ORDER BY rowid").fetchall()
    return [row["name"] for row in rows]


def table_rows(table):
    """Every row of one table, for the Database page."""
    if table not in table_names():  # the name comes from the database itself, never from the user
        raise ValueError(f"No table called {table}.")
    with connect() as conn:
        cursor = conn.execute(f"SELECT * FROM {table} ORDER BY rowid")
        columns = [c[0] for c in cursor.description]
        return columns, [tuple(row) for row in cursor.fetchall()]
