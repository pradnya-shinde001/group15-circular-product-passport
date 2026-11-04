from typing import ClassVar

from .event_hasher import EventHasher
from .lifecycle_event import LifecycleEvent


class EventLedger:

    GENESIS_HASH = "GENESIS"

    EVENT_PERMISSIONS: ClassVar[dict[str, list[str]]] = {
        "manufactured": ["admin", "manufacturer"],
        "sold": ["admin", "manufacturer", "consumer"],
        "used": ["admin", "consumer"],
        "repaired": ["admin", "manufacturer", "consumer"],
        "refurbished": ["admin", "manufacturer", "recycler"],
        "recycled": ["admin", "recycler"]
    }

    def __init__(self, score_engine_callback=None):
        """Constructor."""
        self.initialize(score_engine_callback)

    # Initialization

    def initialize(self, score_engine_callback=None):
        """Initialization method."""

        if hasattr(self, "_events"):
            raise ValueError("EventLedger is already initialized.")

        self._genesis_hash = self.GENESIS_HASH
        self._events = {}
        self._score_engine_callback = score_engine_callback
        self._event_hasher = EventHasher()

    # Getters

    def get_genesis_hash(self):
        return self._genesis_hash

    def get_history(self, product_uuid):
        return list(self._events.get(product_uuid, []))

    def get_events(self):
        return [event for history in self._events.values() for event in history]

    # Setters

    def set_genesis_hash(self, genesis_hash):

        if self._events:
            raise ValueError("Cannot change genesis hash after recording events.")

        if not isinstance(genesis_hash, str) or not genesis_hash:
            raise ValueError("Genesis hash must be a non-empty string.")

        self._genesis_hash = genesis_hash

    # Add lifecycle event

    def add_event(self, product, actor, event_type, details):

        product_uuid = product.get_uuid()
        actor_email = actor.get_email()
        actor_role = actor.get_role()

        if event_type not in LifecycleEvent.EVENT_TYPES:
            raise ValueError("Invalid event type.")

        allowed_roles = self.EVENT_PERMISSIONS[event_type]

        if actor_role not in allowed_roles:
            raise PermissionError("User is not allowed to add this event.")

        history = self._events.get(product_uuid, [])
        previous_hash = history[-1].get_event_hash() if history else self._genesis_hash

        event = LifecycleEvent(product_uuid, event_type, actor_email, details, previous_hash)

        event_hash = self._event_hasher.calculate_hash(event)
        event.set_event_hash(event_hash)

        self._events.setdefault(product_uuid, []).append(event)

        # Notify score engine

        if self._score_engine_callback is not None:
            self._score_engine_callback(event)

        return event
    