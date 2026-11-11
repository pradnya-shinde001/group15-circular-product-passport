# Subsystem 2 – Event Ledger

The Event Ledger records product lifecycle events and verifies their integrity using SHA-256 hash chaining.

### Main Classes
- `EventLedger` – Records and manages lifecycle events.
- `LifecycleEvent` – Stores event information.
- `EventHasher` – Generates and verifies SHA-256 hashes.
- `ChainVerifier` – Verifies the integrity of the hash chain.

### Error handling

`errors.py` has one base class, `LedgerError`, with a `message`, an HTTP `status_code` and `to_dict()`. Each error is also a normal Python error, so existing `except` blocks keep working.

| Error | Status | Raised when |
| --- | --- | --- |
| `ProductNotFoundError` | 404 | The product does not exist |
| `EventNotPermittedError` | 403 | The user's role may not record this event |
| `InvalidEventError` | 400 | Unknown user or event type, or a wrong date |
| `InvalidEventOrderError` | 409 | The event does not fit the history (for example the first event is not `manufactured`) |
| `ChainConflictError` | 409 | Two events followed the same previous hash at the same moment |
| `LedgerDatabaseError` | 500 | The database failed |

### Requirements
- Python 3.11 or later (the project was tested with Python 3.14)

### Tests

`tests/test_subsystem2.py` has 13 tests

Run from the **project root folder**

**Windows (PowerShell or Command Prompt):**

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m pytest tests/test_subsystem2.py -v
```

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m pytest tests/test_subsystem2.py -v
```