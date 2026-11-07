"""AuthService: Subsystem 1's login. Reading passports is public; changing anything needs a login (FR 8)."""
import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from .auth_repository import AuthRepository
from .passport_repository import UserRepository
from .user import User
from .errors import AccountError

SESSION_HOURS = 8
SIGNUP_ROLES = ("consumer", "manufacturer", "recycler")  # never admin


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _now():
    return datetime.now(timezone.utc)


class AuthService:
    def __init__(self):
        self._repository = AuthRepository()
        self._users = UserRepository()

    def sign_up(self, email, password, role):
        """Create an account and log it in. Returns (user dict, session token).
        Raises AccountError for a bad email, password or role, or an email already in use."""
        if role not in SIGNUP_ROLES:
            raise AccountError("Choose consumer, manufacturer or recycler.")
        try:
            user = User((email or "").strip(), role, password or "")  # the User class checks the data
        except ValueError as error:
            raise AccountError(str(error)) from error
        try:
            self._users.add(user)
        except sqlite3.IntegrityError:
            raise AccountError("An account with this email already exists.") from None
        return self.login(user.get_email(), password)
    
    def login(self, email, password):
        """Check the password with the User class. Returns (user dict, session token).
        Raises ValueError with the same message whether the email or the password is wrong."""
        row = self._repository.user_with_hash((email or "").strip().lower())
        user = None
        if row is not None:
            user = User(row["email"], row["role"])
            user.set_password_hash(row["password_hash"])
        if user is None or not user.check_password(password or ""):
            raise AccountError("Wrong email or password.", status_code=401)
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