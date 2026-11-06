"""Error handling for Subsystem 2 (event ledger). LedgerError is the base class for every error it raises.

The subclasses also inherit from LookupError, PermissionError or ValueError, so the existing
`except` blocks and the "Not found" page in app.py keep working."""


class LedgerError(Exception):
    """A Subsystem 2 error: a message for the user and the matching HTTP status code."""
    status_code = 400

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code

    def __str__(self):
        if isinstance(self.message, list):  # a list of problems reads as one sentence
            return " ".join(self.message)
        return str(self.message)

    def to_dict(self):
        """The error as a dict, ready for a JSON response or a log."""
        return {"error": type(self).__name__, "message": self.message, "status": self.status_code}


class ProductNotFoundError(LedgerError, LookupError):
    """No product has this UUID."""
    status_code = 404


class EventNotPermittedError(LedgerError, PermissionError):
    """The user's role may not record this type of event."""
    status_code = 403


class InvalidEventError(LedgerError, ValueError):
    """The event is wrong: an unknown user or event type, or a bad date.
    `message` is always a list of problems, because app.py shows error.args[0]."""

    def __init__(self, message, status_code=None):
        if isinstance(message, str):
            message = [message]
        super().__init__(message, status_code)


class InvalidEventOrderError(InvalidEventError):
    """The event does not fit the product's history, for example a first event that is not 'manufactured'."""
    status_code = 409


class ChainConflictError(InvalidEventError):
    """Two events tried to follow the same previous event at the same moment. Trying again works."""
    status_code = 409


class LedgerDatabaseError(LedgerError):
    """The database failed while the ledger was working."""
    status_code = 500