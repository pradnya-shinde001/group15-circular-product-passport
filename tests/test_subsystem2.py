"""Subsystem 2's 5 main tests (event ledger): error handling and the hash chain.

They use the temporary database from conftest.py, so your real passport.db is never touched.
Run from the project folder:  python -m pytest tests/test_subsystem2.py -v"""
import sqlite3
import threading
import time
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
from subsystem2_ledger.event_hasher import EventHasher
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


def make_chain(length, role="admin"):
    """A product with `length` events (the first is 'manufactured'). Returns (service, user id, product uuid)."""
    user, product_uuid, ledger = make_user(role), make_product(), LedgerService()
    ledger.add_event(product_uuid, user, "manufactured")
    for number in range(length - 1):  # manufactured, sold, then used and repaired in turn
        event_type = "sold" if number == 0 else ("used" if number % 2 == 1 else "repaired")
        ledger.add_event(product_uuid, user, event_type, f"event {number}")
    return ledger, user, product_uuid


def tamper(sql, parameters=()):
    """Change a stored event directly in the file, the way an attacker would (the trigger is removed first)."""
    raw = sqlite3.connect(db_path())
    raw.execute("DROP TRIGGER IF EXISTS events_no_update")
    raw.execute("DROP TRIGGER IF EXISTS events_no_delete")
    raw.execute(sql, parameters)
    raw.commit()
    raw.close()


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


def test_correction_is_a_new_event_and_the_old_one_stays_unchanged():
    """Event can't be edited. A correction is a new event whose note says what it corrects."""
    ledger, user, product_uuid = make_chain(3)
    before = ledger.history(product_uuid)
    ledger.add_event(product_uuid, user, "repaired", "Correction of event 3: it was the screen, not the battery")
    after = ledger.history(product_uuid)
    assert len(after) == 4
    assert after[:3] == before                      # the old events are exactly as they were
    assert "Correction of event 3" in after[3]["details"]["note"]
    assert after[3]["previous_hash"] == before[2]["event_hash"]
    assert ledger.verify(product_uuid)["valid"] is True


def test_failing_score_engine_does_not_lose_the_event():
    """the event is saved first. A score engine that crashes must not turn the request into an error."""
    def broken_score_engine(event):
        raise RuntimeError("score engine is down")

    user, product_uuid = make_user("admin"), make_product()
    ledger = LedgerService(on_event=broken_score_engine)
    ledger.add_event(product_uuid, user, "manufactured")
    assert len(ledger.history(product_uuid)) == 1


def test_score_engine_is_notified_of_every_new_event():
    """the callback gets each new event."""
    seen = []
    user, product_uuid = make_user("admin"), make_product()
    ledger = LedgerService(on_event=seen.append)
    ledger.add_event(product_uuid, user, "manufactured")
    ledger.add_event(product_uuid, user, "sold")
    assert [event.get_event_type() for event in seen] == ["manufactured", "sold"]


def test_verifying_100_events_takes_less_than_one_second():
    """verifying a chain of 100 events"""
    ledger, _, product_uuid = make_chain(100)
    start = time.perf_counter()
    result = ledger.verify(product_uuid)
    assert time.perf_counter() - start < 1.0
    assert result == {"valid": True, "first_broken_event": None, "events": 100}


def test_adding_an_event_takes_less_than_300_ms():
    """checked on a product that already has 100 events."""
    ledger, user, product_uuid = make_chain(100)  # the last event is 'repaired', so 'used' may follow
    start = time.perf_counter()
    ledger.add_event(product_uuid, user, "used", "one more")
    assert time.perf_counter() - start < 0.3


def test_concurrent_events_never_share_a_previous_hash():
    """8 threads add an event to the same product at the same moment. Each one is saved after the
    previous one, or refused with ChainConflictError."""
    ledger, user, product_uuid = make_chain(3)  # manufactured, sold, used: 'repaired' may follow
    outcomes = []

    def add():
        try:
            ledger.add_event(product_uuid, user, "repaired")
            outcomes.append("saved")
        except InvalidEventError:  # lost the race (conflict, order or timestamp), or the chain has moved on
            outcomes.append("refused")

    threads = [threading.Thread(target=add) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    history = ledger.history(product_uuid)
    previous_hashes = [event["previous_hash"] for event in history]
    assert len(previous_hashes) == len(set(previous_hashes))
    assert len(history) == 3 + outcomes.count("saved")
    assert ledger.verify(product_uuid)["valid"] is True


def test_the_hash_does_not_depend_on_the_order_of_the_keys():
    """The same event data gives the same hash, however the keys were ordered."""
    class Event:
        def __init__(self, data):
            self.data = data

        def get_event_data(self):
            return self.data

    first = {"product_uuid": "p", "event_type": "sold", "timestamp": "t", "actor_email": "a",
             "details": {"note": "n", "part": "screen"}, "previous_hash": "h"}
    second = dict(reversed(list(first.items())))
    second["details"] = {"part": "screen", "note": "n"}
    hasher = EventHasher()
    assert hasher.calculate_hash(Event(first)) == hasher.calculate_hash(Event(second))
    assert len(hasher.calculate_hash(Event(first))) == 64


def test_every_kind_of_tampering_is_detected(monkeypatch, tmp_path):
    """changing the details, the hash, the previous hash or the actor, and removing an event.
    It uses its own database file, because tamper() removes the triggers."""
    monkeypatch.setenv("PASSPORT_DB", str(tmp_path / "tamper-kinds.db"))
    cases = [
        ("UPDATE lifecycle_events SET details = '{\"note\": \"forged\"}' WHERE product_uuid = ? AND event_type = 'repaired'", 3),
        ("UPDATE lifecycle_events SET actor_email = 'someone@else.com' WHERE product_uuid = ? AND event_type = 'repaired'", 3),
        ("UPDATE lifecycle_events SET event_hash = 'f' || substr(event_hash, 2) WHERE product_uuid = ? AND event_type = 'repaired'", 3),
        ("UPDATE lifecycle_events SET previous_hash = 'f' || substr(previous_hash, 2) WHERE product_uuid = ? AND event_type = 'repaired'", 3),
        ("DELETE FROM lifecycle_events WHERE product_uuid = ? AND event_type = 'sold'", 2),
    ]
    for sql, expected_position in cases:
        user, product_uuid, ledger = make_user("admin"), make_product(), LedgerService()
        for event_type in ("manufactured", "sold", "repaired", "used"):
            ledger.add_event(product_uuid, user, event_type)
        assert ledger.verify(product_uuid)["valid"] is True
        tamper(sql, (product_uuid,))
        result = ledger.verify(product_uuid)
        assert result["valid"] is False and result["first_broken_event"] == expected_position, sql

def test_events_must_follow_order():
    """FR1: the order is manufactured, then sold, then used, repaired, refurbished or recycled; nothing after recycled."""
    ledger, user, product_uuid = LedgerService(), make_user("admin"), make_product()
    ledger.add_event(product_uuid, user, "manufactured")
    for too_early in ("used", "repaired", "refurbished", "recycled", "manufactured"):
        with pytest.raises(InvalidEventOrderError):
            ledger.add_event(product_uuid, user, too_early)       # a new product must be sold first
    assert ledger.next_events(product_uuid) == ["sold"]
    for event_type in ("sold", "used", "repaired", "repaired", "sold", "used", "recycled"):
        ledger.add_event(product_uuid, user, event_type)          # a second-hand sale and two repairs are fine
    with pytest.raises(InvalidEventOrderError):
        ledger.add_event(product_uuid, user, "used")              # nothing after recycled
    assert ledger.next_events(product_uuid) == []
    assert ledger.verify(product_uuid)["valid"] is True