"""Error handling for Subsystem 3: our own exception types, and one class that turns any error into a clean answer."""
import logging

logger = logging.getLogger("subsystem3")


class ScoreError(Exception):
    """Base class of every error that Subsystem 3 raises on purpose."""
    status = 500
    code = "score_error"


class ProductNotFoundError(ScoreError, LookupError):
    """There is no product with the given UUID."""
    status = 404
    code = "product_not_found"


class InvalidScoreDataError(ScoreError, ValueError):
    """The data given to the score engine is wrong (for example a total of 120)."""
    status = 400
    code = "invalid_data"


class InvalidConfigError(ScoreError, ValueError):
    """score_config.json is wrong (for example the weights do not sum to 1.0). This is a server problem."""
    status = 500
    code = "invalid_config"


class ScoreErrorHandler:
    """Turns an exception into {"error", "message", "status"}, so the caller (a web view, for example) never sees
    a raw traceback. Our own errors keep their message. Value errors become 400. Anything unexpected is logged
    and answered with a general 500 message, so internal details do not leak."""

    def to_response(self, error):
        if isinstance(error, ScoreError):
            return {"error": error.code, "message": str(error), "status": error.status}
        if isinstance(error, (ValueError, TypeError)):
            return {"error": "invalid_data", "message": str(error), "status": 400}
        logger.exception("Unexpected error in Subsystem 3", exc_info=error)
        return {"error": "internal_error", "message": "Something went wrong. Please try again later.",
                "status": 500}

    def run(self, function, *args, **kwargs):
        """Call function. Returns {"ok": True, "result": ...} or {"ok": False, "error": ..., ...}."""
        try:
            return {"ok": True, "result": function(*args, **kwargs)}
        except Exception as error:  # the handler's job is to catch everything and answer cleanly
            return {"ok": False, **self.to_response(error)}
