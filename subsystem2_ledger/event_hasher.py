import hashlib
import json


class EventHasher:

    def __init__(self):
        """Constructor."""
        self.initialize()

    # Initialization

    def initialize(self):
        """Initialization method."""

        if getattr(self, "_initialized", False):
            raise ValueError("EventHasher is already initialized.")

        self._algorithm = "sha256"
        self._initialized = True

    # Getters

    def get_algorithm(self):
        return self._algorithm

    # Hash calculation

    def calculate_hash(self, event):
        """Calculate SHA-256 hash of a lifecycle event."""

        event_string = json.dumps(event.get_event_data(), sort_keys=True, separators=(",", ":"))

        return hashlib.sha256(event_string.encode("utf-8")).hexdigest()

    # Hash verification

    def verify_hash(self, event):
        """Verify event hash."""

        return self.calculate_hash(event) == event.get_event_hash()