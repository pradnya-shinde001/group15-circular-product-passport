
class ChainVerifier:

    def __init__(self):
        """Constructor."""
        self.initialize()

    # Initialization

    def initialize(self):
        """Initialization method."""
        if hasattr(self, "_result"):
            raise ValueError("ChainVerifier is already initialized.")

        self._genesis_hash = "GENESIS"
        self._result = {
            "valid": True,
            "first_broken_event": None
        }

    # Getters

    def get_genesis_hash(self):
        return self._genesis_hash

    def get_result(self):
        return self._result.copy()

    # Setter

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

            # Recalculate current hash

            if event.calculate_hash() != event.get_event_hash():
                self._result = {"valid": False, "first_broken_event": index + 1}
                return self.get_result()

            previous_hash = event.get_event_hash()

        return self.get_result()

    # Get first broken event

    def first_broken_event(self):
        return self._result["first_broken_event"]
