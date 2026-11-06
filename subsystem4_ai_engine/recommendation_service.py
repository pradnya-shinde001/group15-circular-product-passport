"""RecommendationService: Subsystem 4's work on the shared database.
Asks the Recommender for one product and stores the answer."""
from .errors import ProductNotFoundError
from .llm_adapter import LLMAdapter
from .recommendation_repository import RecommendationRepository
from .recommender import Recommender


class RecommendationService:
    def __init__(self):
        self._repository = None
        self.initialize()

    def initialize(self):
        """Create the repository that reads and saves Subsystem 4's data."""
        self._repository = RecommendationRepository()

    def get_repository(self):
        return self._repository

    def recommend(self, product_uuid, use_llm=True):
        """Return an AIPrediction for one product and save it.
        The LLM answers when use_llm is True and a key is set; otherwise the rule-based advisor does."""
        product = self._repository.product_data(product_uuid)
        if product is None:
            raise ProductNotFoundError(product_uuid)

        if use_llm:
            adapter = LLMAdapter()
        else:
            adapter = None
        recommender = Recommender(adapter)
        prediction = recommender.recommend(product)

        self._repository.add(product_uuid, prediction)
        return prediction

    def history(self, product_uuid):
        """All saved recommendations for one product, newest first."""
        return self._repository.history(product_uuid)
