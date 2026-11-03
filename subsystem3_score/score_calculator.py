"""ScoreCalculator: turns a product's data into a score. Each sub-score is its own function, on a 0-100 scale."""
import math

from .circularity_score import CircularityScore
from .score_weights import ScoreWeights
from .sub_score import SubScore


def _number(value):
    """None for missing data, including the NaN that pandas uses."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return float(value)


def recycled_content_score(materials):
    """The share of the product made from recycled material."""
    return sum(m["percent"] * m["recycled"] / 100 for m in materials) if materials else None


def repairability_score(spare_parts_percent, repair_count):
    """80% from spare-part availability and 20% from repair history. Two repairs earn the full 20%."""
    parts = _number(spare_parts_percent)
    if parts is None:
        return None
    return 0.8 * parts + 0.2 * min(_number(repair_count) or 0, 2) / 2 * 100


def lifespan_score(lifespan_years, category_average_years):
    """50 for a typical lifespan in its category, and 100 for twice that or more."""
    years = _number(lifespan_years)
    if years is None:
        return None
    return min(years / (2 * category_average_years), 1) * 100


def recyclability_score(materials):
    """The share of the product that can be recycled."""
    return sum(m["percent"] for m in materials if m["recyclable"]) if materials else None


def hazard_score(materials):
    """100 minus the share of hazardous material, which works as the penalty."""
    return 100 - sum(m["percent"] for m in materials if m["hazard"]) if materials else None


class ScoreCalculator:
    """Products and scores are kept in memory for now. The database layer belongs to Assignment 3."""

    def __init__(self, weights=None):
        self._weights = None
        self.initialize(weights)

    def initialize(self, weights=None):
        """Load the weights. A config whose weights do not sum to 1.0 stops here with an error."""
        self.weights = weights or ScoreWeights()
        self._products = {}
        self._history = {}

    @property
    def weights(self):
        return self._weights

    @weights.setter
    def weights(self, value):
        if not isinstance(value, ScoreWeights):
            raise TypeError("weights must be ScoreWeights.")
        self._weights = value

    def calculate(self, product, materials, computed_at=None):
        """Return a CircularityScore. The same input always gives the same score."""
        values = {
            "recycled_content": recycled_content_score(materials),
            "repairability": repairability_score(product["spare_parts_percent"], product["repair_count"]),
            "lifespan": lifespan_score(product["expected_lifetime_years"],
                                       self._weights.lifespan_for(product["category"])),
            "recyclability": recyclability_score(materials),
            "hazard": hazard_score(materials),
        }
        weights = self._weights.weights
        total = sum((value or 0) * weights[name] for name, value in values.items())
        subs = [SubScore(name, value, weights[name]) for name, value in values.items()]
        missing = [s.label for s in subs if s.value is None]
        return CircularityScore(product["product_id"], total, subs, missing, computed_at)

    def add_product(self, product, materials):
        """Remember a product, so that its score can be recalculated later."""
        self._products[product["product_id"]] = (dict(product), list(materials))

    def recalculate(self, product_id):
        """Calculate a product's score from its stored data and add it to the history."""
        if product_id not in self._products:
            raise ValueError(f"No product with the ID {product_id}.")
        product, materials = self._products[product_id]
        score = self.calculate(product, materials)
        self._history.setdefault(product_id, []).append(score)
        return score

    def recalculate_all(self):
        """Recalculate every product. Returns how many."""
        for product_id in self._products:
            self.recalculate(product_id)
        return len(self._products)

    def on_event(self, event):
        """The ledger calls this after every new event."""
        if event.event_type == "repaired" and event.corrects_event_id is None:
            self._products[event.product_id][0]["repair_count"] += 1
        self.recalculate(event.product_id)

    def latest(self, product_id):
        """The newest score, or None."""
        history = self._history.get(product_id)
        return history[-1] if history else None

    def history(self, product_id):
        """All scores of a product, oldest first."""
        return list(self._history.get(product_id, []))
