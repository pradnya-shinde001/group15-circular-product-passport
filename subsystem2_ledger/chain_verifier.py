from .event_hasher import EventHasher


class ChainVerifier:

    def __init__(self, genesis_hash="GENESIS"):
        """Constructor."""
        self.initialize(genesis_hash)

    # Initialization

    def initialize(self, genesis_hash="GENESIS"):
        """Initialization method."""

        if hasattr(self, "_result"):
            raise ValueError("ChainVerifier is already initialized.")

        if not isinstance(genesis_hash, str) or not genesis_hash:
            raise ValueError("Genesis hash must be a non-empty string.")

        self._genesis_hash = genesis_hash
        self._result = {"valid": True, "first_broken_event": None}
        self._event_hasher = EventHasher()

    # Getters

    def get_genesis_hash(self):
        return self._genesis_hash

    def get_result(self):
        return self._result.copy()

    # Setters

    def set_genesis_hash(self, genesis_hash):

        if not isinstance(genesis_hash, str) or not genesis_hash:
            raise ValueError("Genesis hash must be a non-empty string.")

        self._genesis_hash = genesis_hash
        self._result = {"valid": True, "first_broken_event": None}

    # Verify event chain

    def verify_chain(self, events):

        previous_hash = self._genesis_hash
        self._result = {"valid": True, "first_broken_event": None}

        for index, event in enumerate(events):

            # Check previous hash

            if event.get_previous_hash() != previous_hash:
                self._result = {"valid": False, "first_broken_event": index + 1}
                return self.get_result()

            # Verify current hash

            if not self._event_hasher.verify_hash(event):
                self._result = {"valid": False, "first_broken_event": index + 1}
                return self.get_result()

            previous_hash = event.get_event_hash()

        return self.get_result()

    # Get first broken event

    def first_broken_event(self):
        return self._result["first_broken_event"]