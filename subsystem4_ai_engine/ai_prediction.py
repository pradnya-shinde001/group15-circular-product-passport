"""AIPrediction: one recommendation made by the AI engine."""
from datetime import datetime


class AIPrediction:
    def __init__(self, action, reason, source):
        self._action = action
        self._reason = reason
        self._source = source
        self._created_at = None
        self.initialize()

    def initialize(self):
        """Save the time this prediction was made."""
        self._created_at = datetime.now().isoformat(timespec="seconds")

    def get_action(self):
        return self._action

    def set_action(self, action):
        self._action = action

    def get_reason(self):
        return self._reason

    def set_reason(self, reason):
        self._reason = reason

    def get_source(self):
        return self._source

    def set_source(self, source):
        self._source = source

    def get_created_at(self):
        return self._created_at

    def set_created_at(self, created_at):
        self._created_at = created_at
