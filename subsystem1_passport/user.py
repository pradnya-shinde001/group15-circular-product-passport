"""User: an account that can own products (UML: User 1 --- * Product, 'owns')."""
import hashlib
import hmac
import os
import re


class User:
    ROLES = ("admin", "manufacturer", "recycler", "consumer")  # four roles (FR 8)
    _EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    def __init__(self, email, role="consumer", password=None):
        """Constructor: sets the initial state."""
        self._email = None
        self._role = None
        self._password_hash = None
        self._products = []
        self.initialize(email, role, password)

    def initialize(self, email, role, password):
        """Initialization method: validates and configures the object."""
        self.set_email(email)
        self.set_role(role)
        if password is not None:
            self.set_password(password)

    # ---- getters ----
    def get_email(self):
        return self._email

    def get_role(self):
        return self._role

    def get_password_hash(self):
        return self._password_hash

    def get_products(self):
        return list(self._products)

    # ---- setters ----
    def set_email(self, email):
        if not isinstance(email, str) or not self._EMAIL_PATTERN.match(email):
            raise ValueError("Invalid email address.")
        self._email = email.lower()

    def set_role(self, role):
        if role not in self.ROLES:
            raise ValueError(f"Role must be one of {self.ROLES}.")
        self._role = role

    def set_password(self, plain_password):
        """Stores only a salted hash, never the plain password (NFR 5).
        PBKDF2 is used for Homework 1 to avoid extra installs; swap to bcrypt
        when the FastAPI layer is added."""
        if not isinstance(plain_password, str) or len(plain_password) < 8:
            raise ValueError("Password must be at least 8 characters.")
        salt = os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", plain_password.encode(), salt, 200_000)
        self._password_hash = salt.hex() + "$" + digest.hex()

    # ---- behaviour ----
    def check_password(self, plain_password):
        if not self._password_hash:
            return False
        salt_hex, digest_hex = self._password_hash.split("$")
        digest = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode(), bytes.fromhex(salt_hex), 200_000
        )
        return hmac.compare_digest(digest.hex(), digest_hex)

    def can_edit(self):
        """Login is required to edit; consumers are read-only (FR 8)."""
        return self._role in ("admin", "manufacturer", "recycler")

    def add_product(self, product):
        self._products.append(product)

    def __repr__(self):
        return f"User(email={self._email!r}, role={self._role!r})"
