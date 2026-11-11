"""Error handling for Subsystem 1. PassportError is the base class for every error it raises.

The subclasses also inherit from ValueError, LookupError or PermissionError, so the existing
`except` blocks and the "Not found" page in app.py keep working."""


class PassportError(Exception):
    """A Subsystem 1 error: a message for the user and the matching HTTP status code."""
    status_code = 400

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code

    def to_dict(self):
        """The error as a dict, ready for a JSON response or a log."""
        return {"error": type(self).__name__, "message": self.message, "status": self.status_code}


class AccountError(PassportError, ValueError):
    """A sign-up or login problem, such as a used email or a wrong password."""


class RegistrationError(PassportError, ValueError):
    """A product registration failed. `message` is the list of every problem found."""


class ProductEditError(PassportError, ValueError):
    """A product edit failed. `message` is the list of every problem found."""


class NotAllowedError(PassportError, PermissionError):
    """The user may not change this product."""
    status_code = 403


class ProductNotFoundError(PassportError, LookupError):
    """No product has this UUID."""
    status_code = 404
