"""SubScore: one of the five parts of a circularity score. A value of None means the data is missing."""
LABELS = {"recycled_content": "Recycled content", "repairability": "Repairability", "lifespan": "Lifespan",
          "recyclability": "Recyclability", "hazard": "Hazard-free materials"}


class SubScore:
    def __init__(self, name, value, weight):
        self.name = name
        self.value = value
        self.weight = weight
        self.initialize()

    def initialize(self):
        """Scores are kept with one decimal place."""
        if self._value is not None:
            self._value = round(self._value, 1)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if value not in LABELS:
            raise ValueError(f"name must be one of {list(LABELS)}.")
        self._name = value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if value is not None and not 0 <= value <= 100:
            raise ValueError("A sub-score must be between 0 and 100.")
        self._value = value

    @property
    def weight(self):
        return self._weight

    @weight.setter
    def weight(self, value):
        if not 0 <= value <= 1:
            raise ValueError("A weight must be between 0 and 1.")
        self._weight = value

    @property
    def label(self):
        return LABELS[self._name]

    @property
    def points(self):
        """What this sub-score adds to the total."""
        return round((self._value or 0) * self._weight, 1)

    def to_dict(self):
        return {"name": self._name, "label": self.label, "value": self._value, "weight": self._weight,
                "points": self.points}
