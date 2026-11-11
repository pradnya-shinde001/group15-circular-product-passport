"""RecommendationService: Subsystem 4's work on the shared database.
Asks the Recommender for one product and stores the answer, identifies photos, and saves ratings."""
from .errors import PredictionNotFoundError, ProductNotFoundError
from .image_classifier import ImageClassifier
from .llm_adapter import LLMAdapter
from .photo_check import PhotoCheck
from .recommendation_repository import RecommendationRepository
from .recommender import Recommender


class RecommendationService:
    def __init__(self):
        self._repository = None
        self._classifier = None
        self._photo_check = None
        self.initialize()

    def initialize(self):
        """Create the objects this service works with. CLIP itself is only loaded when a photo comes in."""
        self._repository = RecommendationRepository()
        self._classifier = ImageClassifier()
        self._photo_check = PhotoCheck()

    def get_repository(self):
        return self._repository

    def get_classifier(self):
        return self._classifier

    def set_classifier(self, classifier):
        self._classifier = classifier

    def get_photo_check(self):
        return self._photo_check

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

    def identify_photo(self, photo_path, keep_photo=False):
        """Check the photo, ask the classifier what it shows, then delete the photo unless keep_photo is True."""
        try:
            self._photo_check.check(photo_path)
            result = self._classifier.classify(photo_path)
            self._repository.add_identification(result)  # keep the result and the model name (NFR 9)
            return result
        finally:
            # finally runs even when check() or classify() raises an error, so no photo is left behind
            if not keep_photo:
                self._photo_check.delete(photo_path)

    def identifications(self):
        """All saved photo identifications, newest first."""
        return self._repository.identifications()

    def rate(self, prediction_id, rating):
        """Save the user's rating (1 to 5) for one saved recommendation."""
        prediction = self._repository.get(prediction_id)
        if prediction is None:
            raise PredictionNotFoundError(f"No recommendation with the id {prediction_id}.")

        prediction.rate(rating)  # raises InvalidRatingError for a rating that is not 1 to 5
        self._repository.save_rating(prediction_id, prediction.get_rating())
        return prediction
