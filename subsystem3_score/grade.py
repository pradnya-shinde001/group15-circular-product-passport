"""Grade: a letter from A to E, and the lowest total score that earns it."""


class Grade:
    def __init__(self, letter, min_score):
        self.letter = letter
        self.min_score = min_score
        self.initialize()

    def initialize(self):
        self._letter = self._letter.upper()

    @property
    def letter(self):
        return self._letter

    @letter.setter
    def letter(self, value):
        if str(value).upper() not in ("A", "B", "C", "D", "E"):
            raise ValueError("A grade must be A, B, C, D or E.")
        self._letter = value

    @property
    def min_score(self):
        return self._min_score

    @min_score.setter
    def min_score(self, value):
        if not 0 <= value <= 100:
            raise ValueError("min_score must be between 0 and 100.")
        self._min_score = value

    @classmethod
    def for_score(cls, total):
        return next(grade for grade in GRADES if total >= grade.min_score)


GRADES = [Grade("A", 80), Grade("B", 65), Grade("C", 50), Grade("D", 35), Grade("E", 0)]
