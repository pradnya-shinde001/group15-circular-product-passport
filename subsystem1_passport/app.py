"""FastAPI application for Subsystem 1.

Run:  uvicorn subsystem1_passport.app:create_app --factory --reload
Then: http://localhost:8000 (web UI), http://localhost:8000/docs 
"""
import logging
import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import api, repository as repo, web
from .database import Database

log = logging.getLogger(__name__)


def _secret_from_env():
    key = os.environ.get("SECRET_KEY")
    if not key:
        log.warning("SECRET_KEY is not set: using a random key, logins end when the server restarts.")
        key = secrets.token_urlsafe(32)
    return key


@dataclass
class Settings:
    database_path: str = field(default_factory=lambda: os.environ.get("DATABASE_PATH", "passport.db"))
    # The address printed in QR codes. Set it to the server's real address before printing labels.
    base_url: str = field(default_factory=lambda: os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000"))
    secret_key: str = field(default_factory=_secret_from_env)
    token_ttl_seconds: int = field(default_factory=lambda: int(os.environ.get("TOKEN_TTL_SECONDS", "28800")))
    admin_email: str | None = field(default_factory=lambda: os.environ.get("ADMIN_EMAIL"))
    admin_password: str | None = field(default_factory=lambda: os.environ.get("ADMIN_PASSWORD"))


def _error(status, detail, **extra):
    return JSONResponse({"detail": detail, **extra}, status_code=status)


def _add_error_handlers(app):
    """Domain errors -> standard HTTP status codes with a JSON body (NFR 8)."""
    @app.exception_handler(repo.IncompleteRegistration)
    async def _incomplete(_req: Request, err):
        return _error(422, str(err), missing_fields=err.missing)

    @app.exception_handler(repo.NotFound)
    async def _not_found(_req: Request, err):
        return _error(404, str(err))

    @app.exception_handler(repo.Conflict)
    async def _conflict(_req: Request, err):
        return _error(409, str(err))

    @app.exception_handler(PermissionError)
    async def _forbidden(_req: Request, err):
        return _error(403, str(err))

    @app.exception_handler(ValueError)
    async def _invalid(_req: Request, err):
        return _error(422, str(err))

    @app.exception_handler(TypeError)
    async def _bad_type(_req: Request, err):
        return _error(422, str(err))


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(
        title="Circular Product Passport - Subsystem 1",
        description="Passport, QR code and web UI. Group 15, FH Dortmund.\n\n"
                    "Log in with **Authorize** (username = email) to try the endpoints that edit data.",
        version="1.0.0",
    )
    app.state.settings = settings
    app.state.database = Database(settings.database_path)

    if settings.admin_email and settings.admin_password:
        with app.state.database.connection() as db:
            try:
                repo.create_user(db, settings.admin_email, settings.admin_password, "admin")
            except repo.Conflict:
                pass  # already there

    app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
    app.include_router(api.router)
    app.include_router(web.router)
    _add_error_handlers(app)
    return app

