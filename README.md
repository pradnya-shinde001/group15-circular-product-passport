# AI-Powered Circular Economy Product Passport

Group 15, Capstone Project, FH Dortmund.
**Homework Assignment 3:** a web app on a shared database for all four subsystems.

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

## Run it

Tested with Python 3.14. Run the commands from the project folder.

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Open http://localhost:8000 for the pages and http://localhost:8000/docs for the API. On its first start, the app creates the database with demo data. To rebuild it, stop the app and run `python -m database.seed`. This also deletes products you registered yourself.

**Optional, AI advice from the LLM:** copy `.env.example` to `.env` and add your KI:connect.NRW key, created at https://chat.kiconnect.nrw under API key management. Without a key, the AI engine uses its rules. Git ignores `.env`.

## Logins

Reading passports is public. To register a product or record an event, log in at `/login`, or sign up at `/signup` as a consumer, manufacturer or recycler. The four demo accounts below use the password `demo-password`, for the local demo only.

| Email | May do |
| ----- | ------ |
| `admin@example.com` | Register products, record every event type |
| `manufacturer@example.com` | Register products; record manufactured, sold, repaired, refurbished |
| `recycler@example.com` | Record refurbished, recycled |
| `consumer@example.com` | Record sold, used, repaired |

## Pages and API

| Address | What it shows |
| ------- | ------------- |
| `/` | Search products, with their latest score and grade |
| `/signup`, `/login` | Create an account, log in and out |
| `/register` | Register a product and its materials (manufacturer or admin) |
| `/passport/{uuid}` | Product, materials, QR code, score, lifecycle history, AI recommendation |
| `/database` | Every table with its rows, read live (not in the menu: open it by its address) |
| `/api/products`, `/api/passports/{uuid}` | Products and whole passports as JSON |
| `/api/passports/{uuid}/verify`, `/api/passports/{uuid}/scores` | Event chain check, score history |

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
- **`database/`** is shared: `schema.sql` (all tables), `connection.py` and `seed.py` (demo data).
- **Each subsystem** adds a `*_repository.py`, which saves and loads its data, and a `*_service.py`, which does its work with its classes from Assignment 1. The subsystems work together through callbacks: a new product or event makes the score engine calculate a new score.

## Database tables

| Subsystem | Table | Main columns |
| --------- | ----- | ------------ |
| 1. Passport | `users` | email, role, password_hash (salted hash, never the password) |
| | `sessions` | token_hash, user_id, expires_at |
| | `products` | uuid, name, category, lifespan_years, spare_parts_percent, condition, owner_id, public_url |
| | `material_components` | product_uuid, material, percent, recycled, recyclable, hazard |
| 2. Event ledger | `lifecycle_events` | product_uuid, event_type, timestamp, actor_email, previous_hash, event_hash. Append-only: database triggers refuse any change or deletion |
| 3. Score engine | `circularity_scores` | product_uuid, total, grade, sub_scores, reason. Every score is kept |
| 4. AI engine | `ai_predictions` | product_uuid, action, reason, source (llm or rules) |

The demo data is 4 users and 100 synthetic products, with lifecycle histories from 2021 to 2025. `database/seed.py` adds them through the subsystems' services, so they pass the same checks as data entered on the pages.


The demo data is synthetic, and the category lifespans in `subsystem3_score/score_config.json` are assumptions. `database/passport.db` is not committed; every computer builds its own.
