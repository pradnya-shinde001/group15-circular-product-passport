"""CircularityScore: one calculated result."""
from datetime import datetime, timezone

from .grade import Grade
from .sub_score import SubScore


class CircularityScore:
    def __init__(self, product_id, total, sub_scores, missing=(), computed_at=None):
        self._product_id = product_id
        self.total = total
        self._sub_scores = list(sub_scores)
        self.missing = missing
        self._computed_at = computed_at
        self.initialize()

    def initialize(self):
        """Round the total to one decimal place, work out the grade, and stamp the time."""
        self._total = round(self._total, 1)
        self._grade = Grade.for_score(self._total)
        if self._computed_at is None:
            self._computed_at = datetime.now(timezone.utc).isoformat(timespec="microseconds")

    @property
    def product_id(self):
        return self._product_id

    @property
    def total(self):
        return self._total

    @total.setter
    def total(self, value):
        if not 0 <= value <= 100:
            raise ValueError("A total must be between 0 and 100.")
        self._total = value

    @property
    def grade(self):
        return self._grade

    @property
    def sub_scores(self):
        return list(self._sub_scores)

    @property
    def missing(self):
        return list(self._missing)

    @missing.setter
    def missing(self, value):
        self._missing = list(value)

    @property
    def incomplete(self):
        """True when some data was missing. The score is still given, and counts that part as zero."""
        return bool(self._missing)

    @property
    def computed_at(self):
        return self._computed_at

    def to_dict(self):
        return {"product_id": self._product_id, "total": self._total, "grade": self._grade.letter,
                "incomplete": self.incomplete, "missing": self.missing, "computed_at": self._computed_at,
                "sub_scores": [s.to_dict() for s in self._sub_scores]}
