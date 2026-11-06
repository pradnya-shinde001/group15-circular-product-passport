"""Subsystem 2's 5 main tests (event ledger): error handling and the hash chain.

They use the temporary database from conftest.py, so your real passport.db is never touched.
Run from the project folder:  python -m pytest tests/test_subsystem2.py -v"""
import sqlite3
import uuid as uuid_module
from datetime import UTC, datetime

import pytest

from database import connect, db_path, init_db
from subsystem2_ledger.errors import (
    ChainConflictError,
    EventNotPermittedError,
    InvalidEventError,
    InvalidEventOrderError,
    LedgerDatabaseError,
    LedgerError,
    ProductNotFoundError,
)
from subsystem2_ledger.ledger_service import LedgerService


def make_user(role):
    """Put a user with this role in the database and return its id."""
    init_db()
    with connect() as conn:
        cursor = conn.execute("INSERT INTO users (email, role, password_hash) VALUES (?, ?, 'not-a-real-hash')",
                              (f"{role}-{uuid_module.uuid4().hex[:8]}@example.com", role))
        return cursor.lastrowid


def make_product():
    """Put a product in the database and return its UUID."""
    init_db()
    product_uuid = str(uuid_module.uuid4())
    with connect() as conn:
        conn.execute("INSERT INTO products (uuid, name, category, lifespan_years, public_url, created_at)"
                     " VALUES (?, 'Test Laptop', 'Laptop', 5, 'http://localhost/test', ?)",
                     (product_uuid, datetime.now(UTC).isoformat()))
    return product_uuid


def test_every_ledger_error_is_a_ledger_error_and_a_normal_python_error():
    """One `except LedgerError` catches them all, and the usual LookupError, PermissionError and
    ValueError blocks keep working. to_dict gives the name, message and status for a JSON response."""
    for error_class in (ProductNotFoundError, EventNotPermittedError, InvalidEventError,
                        InvalidEventOrderError, ChainConflictError, LedgerDatabaseError):
        assert issubclass(error_class, LedgerError)
    assert issubclass(ProductNotFoundError, LookupError)
    assert issubclass(EventNotPermittedError, PermissionError)
    assert issubclass(InvalidEventOrderError, ValueError)
    assert ProductNotFoundError("No product.").to_dict() == {
        "error": "ProductNotFoundError", "message": "No product.", "status": 404}


def test_unknown_product_raises_product_not_found_with_404():
    with pytest.raises(ProductNotFoundError) as caught:
        LedgerService().add_event("does-not-exist", make_user("admin"), "manufactured")
    assert caught.value.status_code == 404


def test_wrong_role_raises_event_not_permitted_with_403():
    with pytest.raises(EventNotPermittedError) as caught:
        LedgerService().add_event(make_product(), make_user("consumer"), "manufactured")
    assert caught.value.status_code == 403
    assert "may not record" in caught.value.message


def test_first_event_must_be_manufactured_raises_order_error_with_409():
    with pytest.raises(InvalidEventOrderError) as caught:
        LedgerService().add_event(make_product(), make_user("consumer"), "sold")
    assert caught.value.status_code == 409
    assert any("first event must be 'manufactured'" in problem for problem in caught.value.message)


def test_changed_event_breaks_the_hash_chain(monkeypatch, tmp_path):
    """Recorded events form a valid chain. Then someone with file access removes the trigger and edits
    event 2, and verification finds it. This test uses its own database file, so the shared test database
    keeps its triggers."""
    monkeypatch.setenv("PASSPORT_DB", str(tmp_path / "tamper.db"))
    user, product_uuid = make_user("manufacturer"), make_product()
    ledger = LedgerService()
    for event_type in ("manufactured", "sold", "repaired"):
        ledger.add_event(product_uuid, user, event_type)
    assert ledger.verify(product_uuid) == {"valid": True, "first_broken_event": None, "events": 3}

    raw = sqlite3.connect(db_path())
    raw.execute("DROP TRIGGER events_no_update")
    raw.execute("""UPDATE lifecycle_events SET details = '{"note": "forged"}' WHERE event_type = 'sold'""")
    raw.commit()
    raw.close()

    assert ledger.verify(product_uuid) == {"valid": False, "first_broken_event": 2, "events": 3}