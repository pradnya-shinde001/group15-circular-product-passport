"""AuthService: Subsystem 1's login. Reading passports is public; changing anything needs a login (FR 8)."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from .auth_repository import AuthRepository
from .user import User

SESSION_HOURS = 8


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _now():
    return datetime.now(timezone.utc)


class AuthService:
    def __init__(self):
        self._repository = AuthRepository()

    def login(self, email, password):
        """Check the password with the User class. Returns (user dict, session token).
        Raises ValueError with the same message whether the email or the password is wrong."""
        row = self._repository.user_with_hash((email or "").strip().lower())
        user = None
        if row is not None:
            user = User(row["email"], row["role"])
            user.set_password_hash(row["password_hash"])
        if user is None or not user.check_password(password or ""):
            raise ValueError("Wrong email or password.")
        token = secrets.token_urlsafe(32)  # the browser keeps the token; the database only keeps its hash
        self._repository.delete_expired(_now().isoformat())
        self._repository.add_session(_hash(token), row["id"],
                                     (_now() + timedelta(hours=SESSION_HOURS)).isoformat())
        return {"id": row["id"], "email": row["email"], "role": row["role"]}, token

    def user_for_token(self, token):
        """The logged-in user (id, email, role), or None for no, unknown or expired sessions."""
        if not token:
            return None
        session = self._repository.session_user(_hash(token))
        if session is None:
            return None
        if datetime.fromisoformat(session["expires_at"]) <= _now():
            self._repository.delete_session(_hash(token))
            return None
        return {"id": session["id"], "email": session["email"], "role": session["role"]}

    def logout(self, token):
        if token:
            self._repository.delete_session(_hash(token))
