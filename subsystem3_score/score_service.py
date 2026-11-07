"""ScoreService: Subsystem 3's work on the shared database.
Calculates a product's circularity score with ScoreCalculator and stores it."""
from .errors import ProductNotFoundError
from .score_calculator import ScoreCalculator
from .score_repository import ScoreRepository


class ScoreService:
    def __init__(self, calculator=None):
        self._calculator = calculator or ScoreCalculator()
        self._repository = ScoreRepository()

    def recalculate(self, product_uuid, reason):
        """Calculate the score from the stored data, save it and return the CircularityScore."""
        data = self._repository.product_data(product_uuid)
        if data is None:
            raise ProductNotFoundError(f"No product with the UUID {product_uuid}.")
        product, materials = data
        score = self._calculator.calculate(product, materials)
        self._repository.add(score, reason)
        return score

    def on_registered(self, product_uuid):
        """Called by Subsystem 1 after a new product is registered."""
        return self.recalculate(product_uuid, "registered")

    def on_event(self, event):
        """Called by Subsystem 2 after each new lifecycle event. A repair raises the repairability sub-score."""
        return self.recalculate(event.get_product_uuid(), f"event: {event.get_event_type()}")

    def latest(self, product_uuid):
        return self._repository.latest(product_uuid)

    def history(self, product_uuid):
        return self._repository.history(product_uuid)
