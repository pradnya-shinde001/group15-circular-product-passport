"""AIPrediction: one AI result, with the model that produced it and its rating."""
import json
from datetime import datetime, timezone
from pathlib import Path

PREDICTIONS_FILE = "predictions.jsonl"


class AIPrediction:
    KINDS = ("identification", "recommendation")

    def __init__(self, kind, result, model_name, version, product_id=None, rating=None, created_at=None):
        # Assigning through the properties means the setters validate the first values too.
        self.kind = kind
        self.result = result
        self.model_name = model_name
        self.version = version
        self.product_id = product_id
        self._rating = None if rating is None else self._valid_rating(rating)
        self._created_at = created_at
        self.initialize()

    def initialize(self):
        """Stamp a new prediction with the current UTC time. A stored one keeps its original time."""
        if self._created_at is None:
            self._created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    @property
    def kind(self):
        return self._kind

    @kind.setter
    def kind(self, value):
        if value not in self.KINDS:
            raise ValueError(f"kind must be one of {self.KINDS}.")
        self._kind = value

    @property
    def result(self):
        return dict(self._result)

    @result.setter
    def result(self, value):
        if not isinstance(value, dict) or not value:
            raise ValueError("result must be a non-empty dict.")
        self._result = dict(value)

    @property
    def model_name(self):
        return self._model_name

    @model_name.setter
    def model_name(self, value):
        if not value:
            raise ValueError("model_name is required.")
        self._model_name = value

    @property
    def version(self):
        return self._version

    @version.setter
    def version(self, value):
        if not value:
            raise ValueError("version is required.")
        self._version = value

    @property
    def product_id(self):
        return self._product_id

    @product_id.setter
    def product_id(self, value):
        self._product_id = value

    @property
    def rating(self):
        return self._rating

    @rating.setter
    def rating(self, stars):
        self._rating = self._valid_rating(stars)

    @staticmethod
    def _valid_rating(stars):
        if stars not in (1, 2, 3, 4, 5):
            raise ValueError("A rating must be 1 to 5 stars.")
        return stars

    @property
    def created_at(self):
        """Read-only, because the time a prediction was made must not change."""
        return self._created_at

    def to_dict(self):
        return {"kind": self._kind, "result": self._result, "model_name": self._model_name, "version": self._version,
                "product_id": self._product_id, "rating": self._rating, "created_at": self._created_at}

    def save(self, path=PREDICTIONS_FILE):
        """Add this prediction to the file as one line of JSON. Earlier lines are kept."""
        with open(path, "a") as file:
            file.write(json.dumps(self.to_dict()) + "\n")
        return self

    @classmethod
    def latest(cls, kind, product_id, path=PREDICTIONS_FILE):
        """The newest saved prediction of this kind for this product, or None."""
        if not Path(path).exists():
            return None
        with open(path) as file:
            rows = [json.loads(line) for line in file]
        for row in reversed(rows):
            if row["kind"] == kind and row["product_id"] == product_id:
                return cls(**row)
        return None
