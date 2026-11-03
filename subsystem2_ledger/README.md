# Subsystem 2 – Event Ledger

The Event Ledger records product lifecycle events and verifies their integrity using SHA-256 hash chaining.

### Main Classes
- `EventLedger` – Records and manages lifecycle events.
- `LifecycleEvent` – Stores event information.
- `EventHasher` – Generates and verifies SHA-256 hashes.
- `ChainVerifier` – Verifies the integrity of the hash chain.

### Requirements
- Python 3.10 or later

### Execution

Run from the project root directory:

```bash
python -m subsystem2_ledger.demo
```

**Note:** Events are currently stored in memory. Currently No database is used