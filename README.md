# AI-Powered Circular Economy Product Passport

Group 15, Capstone Project, FH Dortmund.

A digital passport for electronic products: a unique identity and QR code, a tamper-evident lifecycle history, a circularity score, and an AI engine that recognises products from a photo and advises what to do with them.

## Team

| Team member        | Subsystem                                | Folder                                        |
| ------------------ | ---------------------------------------- | --------------------------------------------- |
| Mosaddeka Mallick  | 1. Passport, QR code and web UI          | [subsystem1_passport](subsystem1_passport/)   |
| Anishkumar Sukumar | 2. Event ledger (tamper-evident history) | [subsystem2_ledger](subsystem2_ledger/)       |
| Rajib Munshi       | 3. Circularity score engine              | [subsystem3_score](subsystem3_score/)         |
| Pradnya Shinde     | 4. AI engine (identification and advice) | [subsystem4_ai_engine](subsystem4_ai_engine/) |

**Video:** TODO

## What it does

All four subsystems save their data in **one shared SQLite database** (`database/passport.db`), and a **FastAPI** web app shows it as web pages and as a JSON API.

| Subsystem | Answers the question | Main features |
| --------- | -------------------- | ------------- |
| 1. Passport | What is the product? | Accounts and roles, product registration with materials, QR code, editing name and model |
| 2. Event ledger | What happened to it? | Lifecycle events (manufactured, sold, used, repaired, refurbished, recycled), linked by SHA-256 hashes so any change is detected |
| 3. Score engine | How circular is it? | A score from 0 to 100 and a grade, from five sub-scores; recalculated after every event |
| 4. AI engine | What should happen next? | Recognises the product and its material from a photo (CLIP); recommends repair, resale, reuse or recycling (LLM, with rules as a fallback); users rate each recommendation |

## Run it

Tested with Python 3.14. Run the commands from the project folder.

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Open http://localhost:8000 for the pages and http://localhost:8000/docs for the API. On its first start, the app creates the database with demo data. To rebuild it, stop the app and run `python -m database.seed`. This also deletes products you registered yourself.

**Optional, identify products from a photo:** `pip install torch transformers`. These are large, so they are not in `requirements.txt`. The CLIP model (about 600 MB) downloads once and then loads in the background when the app starts. Without them, everything else works; only the photo upload is unavailable.

**Optional, AI advice from the LLM:** copy `.env.example` to `.env` and add your KI:connect.NRW key, created at https://chat.kiconnect.nrw under API key management. Without a key, the AI engine uses its rules. Git ignores `.env`.

## Logins

Reading passports is public. To register or edit a product, record an event, or get a new AI recommendation, log in at `/login`, or sign up at `/signup` as a consumer, manufacturer or recycler. The four demo accounts below use the password `demo-password`, for the local demo only.

| Email | May do |
| ----- | ------ |
| `admin@example.com` | Register and edit products, record every event type |
| `manufacturer@example.com` | Register products and edit its own; record manufactured, sold, repaired, refurbished |
| `recycler@example.com` | Record refurbished, recycled |
| `consumer@example.com` | Record sold, used, repaired |

A new recommendation needs a login because it may call the paid LLM. Rating a recommendation needs no login, so customers can rate it quickly.

## Pages and API

| Address | What it shows |
| ------- | ------------- |
| `/` | Search products, with their latest score and grade |
| `/signup`, `/login` | Create an account, log in and out |
| `/register` | Register a product and its materials (manufacturer or admin). Optional: upload a photo to fill in the form |
| `/passport/{uuid}` | Product, materials, QR code, score, lifecycle history, AI recommendation with rating |
| `/passport/{uuid}/edit` | Change the name and model (the manufacturer who registered it, or an admin) |
| `/database` | Every table with its rows, read live (not in the menu: open it by its address) |
| `/api/products`, `/api/passports/{uuid}` | Products and whole passports as JSON |
| `/api/passports/{uuid}/events`, `/verify`, `/scores` | Event history, event chain check, score history |

## How it is organised

```mermaid
flowchart LR
    Browser -->|HTTP| App["app.py<br/>pages and API"]
    App --> S1["Subsystem 1<br/>PassportService<br/>AuthService"]
    App --> S2["Subsystem 2<br/>LedgerService"]
    App --> S3["Subsystem 3<br/>ScoreService"]
    App --> S4["Subsystem 4<br/>RecommendationService"]
    S1 --> DB[("database/<br/>passport.db")]
    S2 --> DB
    S3 --> DB
    S4 --> DB
```

- **`app.py` and `templates/`** are the web app. It has no business rules and no SQL; every page asks one of the subsystems.
- **`database/`** is shared: `schema.sql` (all tables), `connection.py` and `seed.py` (4 demo users and 100 synthetic products with histories from 2021 to 2025).
- **Each subsystem** has a `*_repository.py`, which saves and loads its data, and a `*_service.py`, which does its work with its classes. A new product or event makes the score engine calculate a new score.

| Subsystem | Tables |
| --------- | ------ |
| 1. Passport | `users`, `sessions`, `products`, `material_components` |
| 2. Event ledger | `lifecycle_events` (append-only: database triggers refuse any change or deletion) |
| 3. Score engine | `circularity_scores` (every score is kept) |
| 4. AI engine | `ai_predictions` (action, reason, source, model, rating), `photo_identifications` (category, material, confidence, model; the photo itself is never kept) |

## Error handling

Each subsystem has an `errors.py` with one base class and smaller classes for each kind of problem, so other code can catch all errors of a subsystem with one `except`, or only one kind. Most classes also inherit from a built-in error (`ValueError`, `LookupError` or `PermissionError`), so the web app shows a clear message or a "Not found" page instead of crashing.

| Subsystem | Base class | Error classes |
| --------- | ---------- | ------------- |
| 1. Passport | `PassportError` | `AccountError`, `RegistrationError`, `ProductNotFoundError` |
| 2. Event ledger | `LedgerError` | `ProductNotFoundError`, `EventNotPermittedError`, `InvalidEventError`, `InvalidEventOrderError`, `ChainConflictError`, `LedgerDatabaseError` |
| 3. Score engine | `ScoreError` | `ProductNotFoundError`, `InvalidScoreDataError`, `InvalidConfigError` (and `ScoreErrorHandler`, which hides internal details) |
| 4. AI engine | `AIEngineError` | `ProductNotFoundError`, `InvalidProductError`, `InvalidPhotoError`, `InvalidRatingError`, `PredictionNotFoundError`, `LLMError` (caught by the `Recommender`, which then uses the rules) |

## Tests

```bash
python -m pytest -v
```

The tests use a **temporary database**, so they never change `database/passport.db`. The app uses the real LLM and CLIP, but the tests replace them with small fake classes that give fixed answers. That way the tests cost nothing (no paid LLM calls), need no internet or API key, always give the same result, and run in about a second, with or without `torch`. The code around the LLM and CLIP is still tested, for example how the `Recommender` reads the LLM's answer and falls back to the rules when the LLM is down.

| File | Tests | What they check |
| ---- | ----- | --------------- |
| [test_subsystem1.py](tests/test_subsystem1.py) | 5 | Sign-up and login, product registration with passport and QR code, error classes |
| [test_subsystem2.py](tests/test_subsystem2.py) | 14 | Event order and roles, hash chain and tamper detection, concurrency, speed, link to the score engine |
| [test_subsystem3_score.py](tests/test_subsystem3_score.py) | 5 | Score and grade, missing data, errors, score after a repair |
| [test_subsystem4_ai_engine.py](tests/test_subsystem4_ai_engine.py) | 24 | Rules and LLM fallback, LLM reason, photo checks, top 3 and uncertain marks, photo deletion, rating, model names, form pre-fill, accuracy check |

Current result: **51 passed** (48 tests; one runs with 4 different ratings).

## Known limitations

- The demo data is synthetic, and the category lifespans in `subsystem3_score/score_config.json` are assumptions.
- The AI engine uses the circularity score as the product's reusability, because products have no separate reusability value yet.
- Material guesses from a photo are less reliable than category guesses, so the form only fills in a material CLIP is fairly sure of, and the user should check it.
- Matching passports are found by category, not by comparing photos.
- `database/passport.db` is not committed; every computer builds its own.
