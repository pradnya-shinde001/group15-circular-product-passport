"""The shared database used by all four subsystems (SQLite, file: database/passport.db).
This folder only opens the database and creates its tables. Each subsystem keeps its own
code for reading and writing its data, in its own folder."""
from .connection import connect, db_path, init_db, table_names, table_rows

__all__ = ["connect", "db_path", "init_db", "table_names", "table_rows"]
