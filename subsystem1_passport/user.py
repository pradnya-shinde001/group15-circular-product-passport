import os
import re

import bcrypt


class User:
    ROLES = ("admin", "manufacturer", "recycler", "consumer")

    PERMISSIONS = {
        "admin": {"register_product", "edit_any_product", "edit_own_product",
                  "archive_product", "manage_users", "add_event"},
        "manufacturer": {"register_product", "edit_own_product", "add_event"},
        "recycler": {"add_event"},
        "consumer": {"add_event"},
    }

    BCRYPT_ROUNDS = int(os.environ.get("BCRYPT_ROUNDS", "12"))
    _EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    def __init__(self, email, role="consumer", password=None, password_hash=None):

        self._email = None
        self._role = None
        self._password_hash = None
        self._products = []
        self.initialize(email, role, password, password_hash)

    def initialize(self, email, role, password, password_hash=None):

        self.set_email(email)
        self.set_role(role)
        if password is not None:
            self.set_password(password)
        elif password_hash is not None:
            self.set_password_hash(password_hash)

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
        if not isinstance(email, str) or not self._EMAIL_PATTERN.match(email.strip()):
            raise ValueError("Invalid email address.")
        self._email = email.strip().lower()

    def set_role(self, role):
        if role not in self.ROLES:
            raise ValueError(f"Role must be one of {self.ROLES}.")
        self._role = role

    def set_password(self, plain_password):

        if not isinstance(plain_password, str) or len(plain_password) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if len(plain_password.encode()) > 72:
            raise ValueError("Password must be at most 72 bytes (bcrypt limit).")
        salt = bcrypt.gensalt(rounds=self.BCRYPT_ROUNDS)
        self._password_hash = bcrypt.hashpw(plain_password.encode(), salt).decode()

    def set_password_hash(self, password_hash):
        if not isinstance(password_hash, str) or not password_hash.startswith("$2"):
            raise ValueError("Not a bcrypt hash.")
        self._password_hash = password_hash

    # ---- behaviour ----
    def check_password(self, plain_password):
        if not self._password_hash or not isinstance(plain_password, str):
            return False
        try:
            return bcrypt.checkpw(plain_password.encode(), self._password_hash.encode())
        except ValueError:  # e.g. password longer than 72 bytes
            return False

    def can(self, permission):
        return permission in self.PERMISSIONS[self._role]

    def can_edit(self):
        return self.can("edit_own_product")

    def add_product(self, product):
        self._products.append(product)

    def __repr__(self):
        return f"User(email={self._email!r}, role={self._role!r})"
