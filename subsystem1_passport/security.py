"""Login tokens and FastAPI dependencies (NFR 5: login required to edit).

A token is `<payload>.<signature>`: the payload holds the user id and the expiry time,
the signature is HMAC-SHA256 with SECRET_KEY. The API reads it from the
`Authorization: Bearer ...` header, the web pages from an HttpOnly cookie.
"""
import base64
import hashlib
import hmac
import json
import time

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from . import repository as repo

COOKIE_NAME = "access_token"
# Adds the "Authorize" button to the OpenAPI docs page (/docs).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def create_token(user_id: int, secret: str, ttl_seconds: int) -> str:
    payload = _b64(json.dumps({"sub": user_id, "exp": int(time.time()) + ttl_seconds}).encode())
    signature = _b64(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{signature}"


def read_token(token: str, secret: str):
    """Returns the user id, or None if the token is malformed, forged or expired."""
    try:
        payload, signature = token.split(".")
        expected = _b64(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            return None
        data = json.loads(_unb64(payload))
        if data["exp"] < time.time():
            return None
        return int(data["sub"])
    except (ValueError, KeyError, TypeError, AttributeError):
        return None


# ---------------------------------------------------------------- dependencies
def get_db(request: Request):
    """One sqlite3 connection per request; uncommitted changes are rolled back."""
    with request.app.state.database.connection() as conn:
        yield conn


def optional_user(request: Request, bearer: str | None = Depends(oauth2_scheme),
                  db=Depends(get_db)):
    token = bearer or request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    user_id = read_token(token, request.app.state.settings.secret_key)
    if user_id is None:
        return None
    row = repo.get_user(db, user_id)
    return row if row is not None and row.active else None


def require_user(user=Depends(optional_user)):
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Login required.",
                            headers={"WWW-Authenticate": "Bearer"})
    return user
