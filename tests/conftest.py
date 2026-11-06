"""Test setup. The tests use a temporary database, so your real passport.db is never touched."""
import os
import shutil
import sys
import tempfile
from pathlib import Path

# These must be set BEFORE app.py is imported, because importing it opens the database.
TEMP_FOLDER = tempfile.mkdtemp(prefix="passport-tests-")
os.environ["PASSPORT_DB"] = str(Path(TEMP_FOLDER) / "test.db")
os.environ["KICONNECT_API_KEY"] = ""  # always use the rule-based advisor, never the paid LLM

sys.path.insert(0, str(Path(__file__).parent.parent))  # so `import app` finds the project

import pytest
from fastapi.testclient import TestClient

from app import app


@pytest.fixture
def browser():
    """A fresh browser with no login. Redirects are not followed, so tests can check them."""
    with TestClient(app, follow_redirects=False) as client:
        yield client


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(TEMP_FOLDER, ignore_errors=True)
