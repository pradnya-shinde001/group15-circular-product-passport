"""Subsystem 4's pipeline step. It must come after the steps that add life_left and repairability."""
from stream_core import TransformProcessor

from .recommender import Recommender


class AdviceTransform(TransformProcessor):
    """Asks the Recommender what to do with the product. Uses the rules, not the LLM."""

    def __init__(self):
        self.recommender = Recommender()

    def transform(self, record):
        if record["event"].get_event_type() == "recycled":
            record["advice"] = "None"
            return

        product = {"condition": "Good" if record["life_left"] >= 40 else "Poor",
                   "reusability_score": record["life_left"],
                   "repairability_score": record["repairability"]}
        record["advice"] = self.recommender.recommend(product).get_action()
