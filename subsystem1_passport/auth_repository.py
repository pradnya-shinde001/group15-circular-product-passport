"""Subsystem 1 login data in the shared database: the users' password hashes and the sessions table."""
from database import connect


class AuthRepository:
    def user_with_hash(self, email):
        """id, email, role and password_hash of one user, or None."""
        with connect() as conn:
            row = conn.execute("SELECT id, email, role, password_hash FROM users WHERE email = ?",
                               (email,)).fetchone()
        return dict(row) if row else None

    def add_session(self, token_hash, user_id, expires_at):
        with connect() as conn:
            conn.execute("INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                         (token_hash, user_id, expires_at))

    def session_user(self, token_hash):
        """The user of a session and when the session expires, or None."""
        with connect() as conn:
            row = conn.execute("SELECT u.id, u.email, u.role, s.expires_at FROM sessions s"
                               " JOIN users u ON u.id = s.user_id WHERE s.token_hash = ?", (token_hash,)).fetchone()
        return dict(row) if row else None

    def delete_session(self, token_hash):
        with connect() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))

    def delete_expired(self, now):
        with connect() as conn:
            conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
