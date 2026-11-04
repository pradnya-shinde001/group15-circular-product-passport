"""RuleBasedAdvisor: end-of-life advice from fixed rules, used when the LLM is unavailable."""
from datetime import date


def product_facts(product, circularity_score=None):
    return {
        "name": product["product_name"],
        "category": product["category"],
        "manufacturer": product["manufacturer"],
        "manufacturing_year": int(product["manufacturing_year"]),
        "expected_lifetime_years": int(product["expected_lifetime_years"]),
        "current_condition": product["current_condition"],
        "previous_repairs": int(product["repair_count"]),
        "repairability_score": int(product["repairability_score"]),
        "reusability_score": int(product["reusability_score"]),
        "recyclability_score": int(product["recyclability_score"]),
        "recycled_material_percent": int(product["recycled_material_percent"]),
        "battery_recyclable": bool(product["battery_recyclable"]),
        "circularity_score": circularity_score,
    }


def _years(count):
    count = max(count, 0)
    return f"{count} year" if count == 1 else f"{count} years"


class RuleBasedAdvisor:
    MODEL_NAME = "rule-based-advisor"
    VERSION = "1"

    def __init__(self, resale_reusability=60, reuse_reusability=40, repair_repairability=60, min_resale_years=3):
        self.resale_reusability = resale_reusability
        self.reuse_reusability = reuse_reusability
        self.repair_repairability = repair_repairability
        self.min_resale_years = min_resale_years
        self.initialize()

    def initialize(self, current_year=None):
        """Set the year that the remaining product life is counted from."""
        self.current_year = current_year or date.today().year

    @staticmethod
    def _score(value, name):
        if not 0 <= value <= 100:
            raise ValueError(f"{name} must be between 0 and 100.")
        return value

    @property
    def resale_reusability(self):
        return self._resale_reusability

    @resale_reusability.setter
    def resale_reusability(self, value):
        self._resale_reusability = self._score(value, "resale_reusability")

    @property
    def reuse_reusability(self):
        return self._reuse_reusability

    @reuse_reusability.setter
    def reuse_reusability(self, value):
        self._reuse_reusability = self._score(value, "reuse_reusability")

    @property
    def repair_repairability(self):
        return self._repair_repairability

    @repair_repairability.setter
    def repair_repairability(self, value):
        self._repair_repairability = self._score(value, "repair_repairability")

    @property
    def min_resale_years(self):
        return self._min_resale_years

    @min_resale_years.setter
    def min_resale_years(self, value):
        if value < 0:
            raise ValueError("min_resale_years cannot be negative.")
        self._min_resale_years = value

    @property
    def current_year(self):
        return self._current_year

    @current_year.setter
    def current_year(self, value):
        if value < 1990:
            raise ValueError("current_year is too early.")
        self._current_year = value

    def advise(self, product):
        """Return (action, reason), quoting the product's own values."""
        f = product_facts(product)
        condition = f["current_condition"]
        repairability = f["repairability_score"]
        reusability = f["reusability_score"]
        remaining = f["manufacturing_year"] + f["expected_lifetime_years"] - self._current_year

        if condition in ("Excellent", "Good"):
            if reusability >= self._resale_reusability and remaining >= self._min_resale_years:
                return "Resale", (f"Condition is {condition}, reusability is {reusability}/100 and about "
                                  f"{_years(remaining)} of expected life remain.")
            if reusability >= self._reuse_reusability:
                return "Reuse", (f"Condition is {condition}, reusability is {reusability}/100 and {_years(remaining)} "
                                 "of expected life remain, which suits reuse better than resale.")
        elif repairability >= self._repair_repairability and remaining > 0:
            return "Repair", (f"Condition is {condition}, but repairability is {repairability}/100 and "
                              f"about {_years(remaining)} of expected life remain.")
        return "Recycling", (f"Condition is {condition}, repairability is {repairability}/100, reusability is "
                             f"{reusability}/100 and {_years(remaining)} of expected life remain.")
