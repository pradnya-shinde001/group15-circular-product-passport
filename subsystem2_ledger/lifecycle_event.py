from copy import deepcopy
from datetime import UTC, datetime
from typing import ClassVar


class LifecycleEvent:

    EVENT_TYPES: ClassVar[list[str]] = ["manufactured", "sold", "used", "repaired", "refurbished", "recycled"]

    def __init__(self, product_uuid, event_type, actor_email, details, previous_hash):
        """Constructor."""
        self.initialize(product_uuid, event_type, actor_email, details, previous_hash)

    # Initialization

    def initialize(self, product_uuid, event_type, actor_email, details, previous_hash):
        """Initialization method."""

        if getattr(self, "_sealed", False):
            raise ValueError("Event is already initialized and sealed.")

        if event_type not in self.EVENT_TYPES:
            raise ValueError("Invalid event type.")

        self._sealed = False
        self._product_uuid = product_uuid
        self._event_type = event_type
        self._timestamp = datetime.now(UTC).isoformat()
        self._actor_email = actor_email
        self._details = deepcopy(details)
        self._previous_hash = previous_hash
        self._event_hash = None
        self._sealed = True

    # Check sealed status

    def _check_sealed(self):
        if self._sealed:
            raise ValueError("Event is already sealed.")

    # Getters

    def get_product_uuid(self):
        return self._product_uuid

    def get_event_type(self):
        return self._event_type

    def get_timestamp(self):
        return self._timestamp

    def get_actor_email(self):
        return self._actor_email

    def get_details(self):
        return deepcopy(self._details)

    def get_previous_hash(self):
        return self._previous_hash

    def get_event_hash(self):
        return self._event_hash

    def get_event_data(self):
        return {
            "product_uuid": self._product_uuid,
            "event_type": self._event_type,
            "timestamp": self._timestamp,
            "actor_email": self._actor_email,
            "details": deepcopy(self._details),
            "previous_hash": self._previous_hash
        }

    # Setters

    def set_product_uuid(self, product_uuid):
        self._check_sealed()
        self._product_uuid = product_uuid

    def set_event_type(self, event_type):
        self._check_sealed()

        if event_type not in self.EVENT_TYPES:
            raise ValueError("Invalid event type.")

        self._event_type = event_type

    def set_actor_email(self, actor_email):
        self._check_sealed()
        self._actor_email = actor_email

    def set_details(self, details):
        self._check_sealed()
        self._details = deepcopy(details)

    def set_previous_hash(self, previous_hash):
        self._check_sealed()
        self._previous_hash = previous_hash

    def set_event_hash(self, event_hash):
        """Assign event hash once."""

        if self._event_hash is not None:
            raise ValueError("Event hash is already assigned.")

        if not isinstance(event_hash, str) or not event_hash:
            raise ValueError("Event hash must be a non-empty string.")

        self._event_hash = event_hash