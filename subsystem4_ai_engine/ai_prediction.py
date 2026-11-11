"""AIPrediction: one recommendation made by the AI engine."""
from datetime import datetime

from .errors import InvalidRatingError


class AIPrediction:
    def __init__(self, action, reason, source, model="", rating=None):
        self._action = action
        self._reason = reason
        self._source = source
        self._model = model      # which model answered, with its version, e.g. "GPT-OSS-120B"
        self._rating = rating    # the user's rating, 1 to 5, or None before anyone rates it
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

    def get_model(self):
        return self._model

    def set_model(self, model):
        self._model = model

    def get_rating(self):
        return self._rating

    def rate(self, rating):
        """Save the user's rating. It must be a whole number from 1 to 5."""
        if type(rating) is not int or rating < 1 or rating > 5:
            raise InvalidRatingError("A rating must be a whole number from 1 to 5.")
        self._rating = rating

    def get_created_at(self):
        return self._created_at

    def set_created_at(self, created_at):
        self._created_at = created_at
