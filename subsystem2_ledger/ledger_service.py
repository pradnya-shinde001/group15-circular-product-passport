"""LedgerService: Subsystem 2's work on the shared database.
Adds lifecycle events to a product's hash chain and verifies the chain."""
import logging
import sqlite3
from datetime import datetime

from .chain_verifier import ChainVerifier
from .errors import (
    ChainConflictError,
    EventNotPermittedError,
    InvalidEventError,
    InvalidEventOrderError,
    LedgerDatabaseError,
    ProductNotFoundError,
)
from .event_hasher import EventHasher
from .event_ledger import EventLedger
from .ledger_repository import LedgerRepository
from .lifecycle_event import LifecycleEvent

EVENT_PERMISSIONS = EventLedger.EVENT_PERMISSIONS

# Order of events: each event type can only follow certain previous event types. The first event must be "manufactured".
NEXT_EVENTS = {
    None: ["manufactured"],
    "manufactured": ["sold"],
    "sold": ["used", "repaired", "refurbished", "recycled"],
    "used": ["sold", "repaired", "refurbished", "recycled"],
    "repaired": ["used", "sold", "repaired", "refurbished", "recycled"],
    "refurbished": ["sold", "used", "repaired", "recycled"],
    "recycled": [],
}

logger = logging.getLogger(__name__)

class LedgerService:
    def __init__(self, on_event=None):
        """on_event(event) is called after each new event, for example to notify the score engine."""
        self._on_event = on_event
        self._repository = LedgerRepository()
        self._hasher = EventHasher()

    def add_event(self, product_uuid, actor_id, event_type, note="", timestamp=None):
        """Check the role, hash the event onto the chain and save it.
        `timestamp` (optional datetime) records an earlier event; it cannot be before the previous event.
        Raises ProductNotFoundError, EventNotPermittedError, InvalidEventError, InvalidEventOrderError,
        ChainConflictError or LedgerDatabaseError. All of them are LedgerError (see errors.py)."""
        if not self._repository.product_exists(product_uuid):
            raise ProductNotFoundError(f"No product with the UUID {product_uuid}.")
        actor = self._repository.actor(actor_id)
        if actor is None:
            raise InvalidEventError("Choose who records the event.")
        if event_type not in LifecycleEvent.EVENT_TYPES:
            raise InvalidEventError(f"Event type must be one of {', '.join(LifecycleEvent.EVENT_TYPES)}.")
        allowed = EVENT_PERMISSIONS[event_type]
        if actor["role"] not in allowed:
            raise EventNotPermittedError(
                f"A {actor['role']} may not record '{event_type}'. Allowed: {', '.join(allowed)}.")
        self.check_order(product_uuid, event_type)
        previous_hash = self._repository.last_hash(product_uuid) or EventLedger.GENESIS_HASH
        details = {"note": note.strip()} if note and note.strip() else {}
        try:
            event = LifecycleEvent(product_uuid, event_type, actor["email"], details, previous_hash, timestamp)
        except ValueError as e:
            raise InvalidEventError(str(e)) from e
        last_time = self._repository.last_timestamp(product_uuid)
        if last_time is not None and datetime.fromisoformat(event.get_timestamp()) < datetime.fromisoformat(last_time):
            raise InvalidEventError("An event cannot be dated before the product's previous event.")
        event.set_event_hash(self._hasher.calculate_hash(event))
        try:
            self._repository.add(event)
        except sqlite3.IntegrityError as e:  # two events tried to follow the same previous hash
            raise ChainConflictError(["Another event was added at the same moment. Please try again."]) from e
        except sqlite3.Error as e:
            raise LedgerDatabaseError(f"The database failed: {e}") from e
        if self._on_event is not None:
            try:
                self._on_event(event)
            except Exception:  # the event is already saved, so a failing score engine must not fail the request
                logger.exception("The score engine could not be notified about event %s", event.get_event_hash())
        return event

    def check_order(self, product_uuid, event_type):
        """Check that the new event may follow the product's last event (see NEXT_EVENTS).
        Raises InvalidEventOrderError when it may not."""
        past_events = [event.get_event_type() for event in self._repository.history(product_uuid)]
        last_event = past_events[-1] if past_events else None

        if last_event == "recycled":
            raise InvalidEventOrderError("This product was recycled. No more events can be added.")
        if event_type == "manufactured" and last_event is not None:
            raise InvalidEventOrderError("This product was already manufactured.")
        if event_type not in NEXT_EVENTS[last_event]:
            if last_event is None:
                raise InvalidEventOrderError("The first event must be 'manufactured'.")
            raise InvalidEventOrderError(
                f"After '{last_event}' the next event must be: {' or '.join(NEXT_EVENTS[last_event])}.")

    def next_events(self, product_uuid):
        """The event types that may be added next to this product."""
        history = self._repository.history(product_uuid)
        return NEXT_EVENTS[history[-1].get_event_type() if history else None]

    def history(self, product_uuid):
        """All events as dicts, oldest first."""
        return [e.to_dict() for e in self._repository.history(product_uuid)]

    def verify(self, product_uuid):
        """{"valid": bool, "first_broken_event": position or None, "events": count}"""
        events = self._repository.history(product_uuid)
        result = ChainVerifier(EventLedger.GENESIS_HASH).verify_chain(events)
        return {**result, "events": len(events)}