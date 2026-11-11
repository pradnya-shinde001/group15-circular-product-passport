"""The errors of Subsystem 4 (AI engine).

Every error of this subsystem inherits from AIEngineError, so other code can catch
all of them with one `except AIEngineError:`, or only one kind, for example `except LLMError:`."""


class AIEngineError(Exception):
    """Base class for every error of the AI engine."""


class ProductNotFoundError(AIEngineError, LookupError):
    """There is no product with this UUID.
    It is also a LookupError, so the web app shows its normal "Not found" page."""

    def __init__(self, product_uuid):
        self.product_uuid = product_uuid
        super().__init__(f"No product with the UUID {product_uuid}.")


class InvalidProductError(AIEngineError, ValueError):
    """The product data is missing something the advisor needs, such as its condition."""


class InvalidPhotoError(AIEngineError, ValueError):
    """The photo is not a JPG or PNG, or it is bigger than 10 MB."""


class InvalidRatingError(AIEngineError, ValueError):
    """A rating must be a whole number from 1 to 5."""


class PredictionNotFoundError(AIEngineError, LookupError):
    """There is no saved recommendation with this id."""


class LLMError(AIEngineError):
    """The LLM gave no usable answer: no key, no connection, a timeout, or an answer in the wrong format.
    The Recommender catches this error and uses the rule-based advisor instead."""
