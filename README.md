# AI-Powered Circular Economy Product Passport

Group 15, Capstone Project, FH Dortmund.
**Homework Assignment 4:** error handling with our own exception classes, and automated tests with pytest, on top of the web app and shared database from Assignment 3.

A digital passport for electronic products: a unique identity and QR code, a tamper-evident lifecycle history, a circularity score and AI advice.

## Team

| Team member        | Subsystem                                | Folder                                        |
| ------------------ | ---------------------------------------- | --------------------------------------------- |
| Mosaddeka Mallick  | 1. Passport, QR code and web UI          | [subsystem1_passport](subsystem1_passport/)   |
| Anishkumar Sukumar | 2. Event ledger (tamper-evident history) | [subsystem2_ledger](subsystem2_ledger/)       |
| Rajib Munshi       | 3. Circularity score engine              | [subsystem3_score](subsystem3_score/)         |
| Pradnya Shinde     | 4. AI engine (advice)                    | [subsystem4_ai_engine](subsystem4_ai_engine/) |

**Video:** the link will be added here.

## What we built

All four subsystems save their data in **one shared SQLite database** (`database/passport.db`), and a **FastAPI** web app shows that data as web pages and as a JSON API. SQLite is built into Python and needs no database server.

New in Assignment 4:

- **Error handling.** Subsystems raise their own exception classes instead of plain `ValueError`. The web app turns them into a clear message, never a crash. See [Error handling](#error-handling).
- **Tests.** A pytest suite in [tests/](tests/) checks the error classes, the AI engine and the whole web app. See [Tests](#tests).

## Run the tests

Tested with Python 3.14. Run the commands from the project folder. You don't need to start the web app: the tests run it in memory with FastAPI's test client.

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -v
```

## Error handling

Each subsystem has an `errors.py` with one base class and smaller classes for each kind of problem. Other code can catch every error of a subsystem with one `except`, or only one kind. Each subsystem's `__init__.py` exports its error classes, except Subsystem 1's (import those from `subsystem1_passport.errors`). Most classes also inherit from a built-in error (`ValueError`, `LookupError` or `PermissionError`). That way, the existing `except` blocks and the "Not found" handler in `app.py` from Assignment 3 keep working without changes.

| Subsystem | File | Base class | Error classes (HTTP status) |
| --------- | ---- | ---------- | --------------------------- |
| 1. Passport | [subsystem1_passport/errors.py](subsystem1_passport/errors.py) | `PassportError` | `AccountError` (sign-up or login problem, such as a used email; 401 for a wrong password), `RegistrationError` (lists every problem with a new product), `ProductNotFoundError` (404) |
| 2. Event ledger | [subsystem2_ledger/errors.py](subsystem2_ledger/errors.py) | `LedgerError` | `ProductNotFoundError` (404), `EventNotPermittedError` (the role may not record this event, 403), `InvalidEventError` (unknown user or event type, or a bad date, 400), `InvalidEventOrderError` (event does not fit the history, 409), `ChainConflictError` (two events tried to follow the same event at once, 409), `LedgerDatabaseError` (500) |
| 3. Score engine | [subsystem3_score/errors.py](subsystem3_score/errors.py) | `ScoreError` | `ProductNotFoundError` (404), `InvalidScoreDataError` (wrong score data, such as a total of 120, 400), `InvalidConfigError` (wrong `score_config.json`, such as weights that do not add up to 1.0, 500) |
| 4. AI engine | [subsystem4_ai_engine/errors.py](subsystem4_ai_engine/errors.py) | `AIEngineError` | `ProductNotFoundError`, `InvalidProductError` (product data has no condition or score), `LLMError` (no key, no connection, timeout or an answer in the wrong format) |