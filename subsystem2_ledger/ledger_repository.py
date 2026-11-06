"""Subsystem 2 data in the shared database: the append-only lifecycle_events table."""
import json

from database import connect


class StoredEvent:
    """A lifecycle event read back from the database.
    It has the same getters as LifecycleEvent, so EventHasher and ChainVerifier can check it unchanged."""

    def __init__(self, row):
        self._row = dict(row)
        self._details = json.loads(self._row["details"])

    def get_id(self):
        return self._row["id"]

    def get_product_uuid(self):
        return self._row["product_uuid"]

    def get_event_type(self):
        return self._row["event_type"]

    def get_timestamp(self):
        return self._row["timestamp"]

    def get_actor_email(self):
        return self._row["actor_email"]

    def get_details(self):
        return dict(self._details)

    def get_previous_hash(self):
        return self._row["previous_hash"]

    def get_event_hash(self):
        return self._row["event_hash"]

    def get_event_data(self):
        """Exactly the fields EventHasher hashed when the event was created."""
        return {"product_uuid": self.get_product_uuid(), "event_type": self.get_event_type(),
                "timestamp": self.get_timestamp(), "actor_email": self.get_actor_email(),
                "details": self.get_details(), "previous_hash": self.get_previous_hash()}

    def to_dict(self):
        return {"id": self.get_id(), **self.get_event_data(), "event_hash": self.get_event_hash()}


class LedgerRepository:
    def product_exists(self, product_uuid):
        with connect() as conn:
            return conn.execute("SELECT 1 FROM products WHERE uuid = ?", (product_uuid,)).fetchone() is not None

    def actor(self, user_id):
        """The email and role of the user who records an event, or None."""
        with connect() as conn:
            row = conn.execute("SELECT email, role FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

    def last_hash(self, product_uuid):
        """The newest event's hash, or None when the product has no events yet."""
        with connect() as conn:
            row = conn.execute("SELECT event_hash FROM lifecycle_events WHERE product_uuid = ?"
                               " ORDER BY id DESC LIMIT 1", (product_uuid,)).fetchone()
        return row["event_hash"] if row else None

    def last_timestamp(self, product_uuid):
        """The newest event's timestamp, or None."""
        with connect() as conn:
            row = conn.execute("SELECT timestamp FROM lifecycle_events WHERE product_uuid = ?"
                               " ORDER BY id DESC LIMIT 1", (product_uuid,)).fetchone()
        return row["timestamp"] if row else None

    def add(self, event):
        """Save a hashed LifecycleEvent."""
        with connect() as conn:
            cursor = conn.execute(
                "INSERT INTO lifecycle_events (product_uuid, event_type, timestamp, actor_email, details,"
                " previous_hash, event_hash) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (event.get_product_uuid(), event.get_event_type(), event.get_timestamp(), event.get_actor_email(),
                 json.dumps(event.get_details()), event.get_previous_hash(), event.get_event_hash()))
            return cursor.lastrowid

    def history(self, product_uuid):
        """All events of a product, oldest first, as StoredEvent objects."""
        with connect() as conn:
            rows = conn.execute("SELECT * FROM lifecycle_events WHERE product_uuid = ? ORDER BY id",
                                (product_uuid,)).fetchall()
        return [StoredEvent(row) for row in rows]
