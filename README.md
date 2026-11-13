# AI-Powered Circular Economy Product Passport

[![Tests](https://github.com/pradnya-shinde001/group15-circular-product-passport/actions/workflows/tests.yml/badge.svg)](https://github.com/pradnya-shinde001/group15-circular-product-passport/actions/workflows/tests.yml)


A digital passport for electronic products: a unique identity and QR code, a tamper-evident lifecycle history, a circularity score, and an AI engine that recognises products from a photo and advises what to do with them.



## 1. Team and Responsibilities

| Name | Matriculation No. | Subsystem | Main features | Folder |
| ---- | ----------------- | --------- | ------------- | ------ |
| Mosaddeka Mallick | 7226235 | Passport, QR code and web UI | Accounts and roles, product registration with materials, unique passport with QR code, search, editing name and model | [subsystem1_passport](subsystem1_passport/) |
| Anishkumar Sukumar | 7226163 | Event ledger | Lifecycle events (manufactured, sold, used, repaired, refurbished, recycled) recorded by permitted roles in real-life order, linked by SHA-256 hashes so any change is detected, append-only history, chain verification | [subsystem2_ledger](subsystem2_ledger/) |
| Rajib Munshi | 7225913 | Circularity score engine | Score from 0 to 100 and a grade from five sub-scores, recalculated after every event | [subsystem3_score](subsystem3_score/) |
| Pradnya Shinde | 7226048 | AI engine | Product recognition from a photo (CLIP), repair, resale, reuse or recycling advice (LLM with rule-based fallback), user ratings | [subsystem4_ai_engine](subsystem4_ai_engine/) |

## Project Demonstration Video

[Demonstration video](https://drive.google.com/file/d/14slt4f9fq5XE8N5p-PykLuiCyrFBE7Dd/view?usp=drive_link)

---

## 2. System Design

### 2.1 Architecture

```mermaid
flowchart LR
    Browser -->|HTTP| App["app.py<br/>pages and API"]
    App --> S1["Passport<br/>PassportService<br/>AuthService"]
    App --> S2["Event ledger<br/>LedgerService"]
    App --> S3["Score engine<br/>ScoreService"]
    App --> S4["AI engine<br/>RecommendationService"]
    S1 --> DB[("database/<br/>passport.db")]
    S2 --> DB
    S3 --> DB
    S4 --> DB
```

- `app.py` and `templates/` are the web app. It has no business rules and no SQL; every page asks one of the subsystems.
- All four subsystems save their data in one shared SQLite database. Each subsystem has a `*_repository.py`, which saves and loads its data, and a `*_service.py`, which does its work with its classes.
- The web app is the only entry point. It talks to each subsystem **only through its service class** (the interface). The subsystems never import each other; `app.py` connects them by passing a callback into the constructor.
- Interaction between subsystems (callbacks set in `app.py`):
  - `PassportService(on_registered=ScoreService.on_registered)`: a new product gets its first score.
  - `LedgerService(on_event=ScoreService.on_event)`: every saved lifecycle event recalculates the score.
  - `RecommendationService` reads the product and score data through its own repository.

#### Interaction: adding a lifecycle event

```mermaid
sequenceDiagram
    actor User
    participant App as app.py
    participant LS as LedgerService
    participant LR as LedgerRepository
    participant SS as ScoreService
    User->>App: POST /passport/{uuid}/events
    App->>LS: add_event(uuid, user_id, event_type, note)
    LS->>LR: product_exists(), actor()
    LS->>LS: check role and order
    LS->>LR: last_hash(uuid)
    LS->>LS: create LifecycleEvent, calculate_hash()
    LS->>LR: add(event)
    LS->>SS: on_event(event)
    SS-->>LS: new score saved
    LS-->>App: event
    App-->>User: "Event added"
```

### 2.2 Class Diagrams

Notation: `+` public, `-` private, underline = static, `*--` composition, `o--` aggregation, `-->` association, `..>` dependency, `<|--` inheritance. Every subsystem is used through one service class (marked `<<service>>`), which is its interface. Repositories (`<<repository>>`) are the only classes that run SQL.

#### Passport

**Purpose:** Registers users and products, creates the digital passport and QR code, and controls who may edit.
**Interface:** `PassportService` (`register_product`, `get_product`, `search`, `update_details`, `qr_png`) and `AuthService` (`sign_up`, `login`, `user_for_token`, `logout`).

```mermaid
classDiagram
    direction TB
    class User {
        +ROLES: tuple$
        -email: str
        -role: str
        -password_hash: str
        -products: list
        +get_email() str
        +set_email(email)
        +get_role() str
        +set_role(role)
        +set_password(password)
        +check_password(plain_password) bool
        +can_edit() bool
        +add_product(product)
    }
    class Product {
        -uuid: str
        -name: str
        -model: str
        -category: str
        -lifespan_years: int
        -owner: User
        -materials: list
        +get_name() str
        +set_name(name)
        +add_material(component)
        +total_percent() float
        +materials_valid() bool
        +missing_fields() list
        +validate()
    }
    class MaterialComponent {
        -material: str
        -percent: float
        -recycled: bool
        -hazard: bool
        +get_percent() float
        +set_percent(percent)
        +is_recycled() bool
        +is_hazard() bool
        +to_dict() dict
    }
    class Passport {
        -product: Product
        -public_url: str
        -qr_code: QRCode
        -history: list
        +get_public_url() str
        +set_public_url(url)
        +add_history_event(description)
        +export_json() str
    }
    class QRCode {
        -target_url: str
        -png_bytes: bytes
        +get_target_url() str
        +set_target_url(url)
        +generate() bytes
        +save(path)
    }
    class PassportService {
        <<service>>
        -users: UserRepository
        -products: ProductRepository
        -on_registered: Callable
        +register_product(name, category, lifespan_years, model, owner_id, spare_parts_percent, condition, materials) str
        +get_product(uuid) dict
        +materials(uuid) list
        +search(text) list
        +can_edit(product, user) bool
        +update_details(uuid, user, name, model)
        +qr_png(uuid) bytes
    }
    class AuthService {
        <<service>>
        -repository: AuthRepository
        -users: UserRepository
        +sign_up(email, password, role) User
        +login(email, password)
        +user_for_token(token)
        +logout(token)
    }
    class ProductRepository {
        <<repository>>
        +add(product, materials, public_url, owner_id, spare_parts_percent, condition)
        +get(uuid) dict
        +materials(uuid) list
        +search(text) list
        +update_details(uuid, name, model)
    }
    class UserRepository {
        <<repository>>
        +add(user)
        +get(user_id)
        +all() list
    }
    class AuthRepository {
        <<repository>>
        +user_with_hash(email)
        +add_session(token_hash, user_id, expires_at)
        +session_user(token_hash)
        +delete_session(token_hash)
    }
    User "1" --> "0..*" Product : owns
    Product "1" *-- "1..*" MaterialComponent : made of
    Passport "1" --> "1" Product : describes
    Passport "1" *-- "1" QRCode : has
    PassportService *-- UserRepository
    PassportService *-- ProductRepository
    PassportService ..> Passport : creates
    PassportService ..> User : creates
    AuthService *-- AuthRepository
    AuthService *-- UserRepository
    AuthService ..> User : creates
```

#### Event Ledger

**Purpose:** Keeps a tamper-evident, append-only history of a product's life. Each event stores the hash of the previous one, so any change is detected.
**Interface:** `LedgerService` (`add_event`, `check_order`, `next_events`, `history`, `verify`). It checks the actor's role and the event order and raises a `LedgerError` with an HTTP code when a rule is broken.

```mermaid
classDiagram
    direction TB
    class LedgerService {
        <<service>>
        -repository: LedgerRepository
        -hasher: EventHasher
        -on_event: Callable
        +add_event(product_uuid, actor_id, event_type, note) LifecycleEvent
        +check_order(product_uuid, event_type)
        +next_events(product_uuid) list
        +history(product_uuid) list
        +verify(product_uuid) dict
    }
    class LifecycleEvent {
        +EVENT_TYPES: list$
        -product_uuid: str
        -event_type: str
        -timestamp: str
        -actor_email: str
        -details: dict
        -previous_hash: str
        -event_hash: str
        +get_event_data() dict
        +get_event_hash() str
        +get_previous_hash() str
        +set_event_hash(event_hash)
    }
    class StoredEvent {
        -row: dict
        +get_event_data() dict
        +get_event_hash() str
        +get_previous_hash() str
        +to_dict() dict
    }
    class EventHasher {
        -algorithm: str
        +calculate_hash(event) str
        +verify_hash(event) bool
    }
    class ChainVerifier {
        -genesis_hash: str
        -result: dict
        -event_hasher: EventHasher
        +verify_chain(events) dict
        +first_broken_event() int
        +get_result() dict
    }
    class EventLedger {
        +GENESIS_HASH: str$
        +EVENT_PERMISSIONS: dict$
        -events: dict
        -genesis_hash: str
        -score_engine_callback: Callable
        -event_hasher: EventHasher
        +add_event(product, actor, event_type, details) LifecycleEvent
        +get_history(product_uuid) list
        +get_events() list
    }
    class LedgerRepository {
        <<repository>>
        +product_exists(product_uuid) bool
        +actor(user_id) dict
        +last_hash(product_uuid) str
        +last_timestamp(product_uuid) str
        +add(event) int
        +history(product_uuid) list
    }
    LedgerService *-- LedgerRepository
    LedgerService *-- EventHasher
    LedgerService ..> LifecycleEvent : creates
    LedgerService ..> ChainVerifier : creates
    LedgerService ..> EventLedger : reads permissions
    LedgerRepository ..> StoredEvent : creates
    EventLedger "1" o-- "0..*" LifecycleEvent : records
    EventLedger *-- EventHasher
    ChainVerifier *-- EventHasher
    EventHasher ..> LifecycleEvent : hashes
    ChainVerifier ..> LifecycleEvent : verifies
```

#### Score Engine

**Purpose:** Calculates the circularity score (0-100) and grade from the product data and keeps the score history.
**Interface:** `ScoreService` (`recalculate`, `on_registered`, `on_event`, `latest`, `history`).

```mermaid
classDiagram
    direction TB
    class ScoreService {
        <<service>>
        -calculator: ScoreCalculator
        -repository: ScoreRepository
        +recalculate(product_uuid, reason)
        +on_registered(product_uuid)
        +on_event(event)
        +latest(product_uuid)
        +history(product_uuid) list
    }
    class ScoreRepository {
        <<repository>>
        +product_data(product_uuid) dict
        +add(score, reason)
        +latest(product_uuid)
        +history(product_uuid) list
    }
    class ScoreCalculator {
        -weights: ScoreWeights
        -products: dict
        -history: dict
        +calculate(product, materials, computed_at) CircularityScore
        +add_product(product, materials)
        +recalculate(product_id)
        +recalculate_all()
        +on_event(event)
        +latest(product_id)
        +history(product_id) list
    }
    class ScoreWeights {
        -config_path: Path
        -weights: dict
        -category_lifespans: dict
        +lifespan_for(category) int
    }
    class CircularityScore {
        -product_id: str
        -total: float
        -grade: Grade
        -sub_scores: list
        -missing: list
        -computed_at: str
        +incomplete() bool
        +to_dict() dict
    }
    class SubScore {
        -name: str
        -value: float
        -weight: float
        +label() str
        +points() float
        +to_dict() dict
    }
    class Grade {
        -letter: str
        -min_score: int
        +for_score(total) Grade$
    }
    ScoreService *-- ScoreCalculator
    ScoreService *-- ScoreRepository
    ScoreCalculator *-- ScoreWeights
    ScoreCalculator ..> CircularityScore : creates
    ScoreCalculator ..> SubScore : creates
    CircularityScore "1" *-- "5" SubScore : has
    CircularityScore "1" *-- "1" Grade : has
```

#### AI Engine

**Purpose:** Identifies a product from a photo and recommends an end-of-life action (repair, resell, recycle...); falls back to rules when the LLM is unavailable.
**Interface:** `RecommendationService` (`identify_photo`, `recommend`, `rate`, `history`, `identifications`).

```mermaid
classDiagram
    direction TB
    class RecommendationService {
        <<service>>
        -repository: RecommendationRepository
        -classifier: ImageClassifier
        -photo_check: PhotoCheck
        +identify_photo(photo_path, keep_photo)
        +recommend(product_uuid, use_llm)
        +rate(prediction_id, rating)
        +history(product_uuid) list
        +identifications() list
    }
    class RecommendationRepository {
        <<repository>>
        +product_data(product_uuid) dict
        +add(product_uuid, prediction)
        +get(prediction_id)
        +add_identification(result)
        +identifications() list
        +save_rating(prediction_id, rating)
        +history(product_uuid) list
    }
    class PhotoCheck {
        -max_megabytes: int
        -allowed_formats: tuple
        +check(photo_path)
        +delete(photo_path)
    }
    class ImageClassifier {
        -model_name: str
        -uncertain_below: float
        -categories: list
        -materials: list
        +is_loaded() bool
        +load()
        +classify(photo_path)
        +top_predictions(labels, confidences, top) list
    }
    class AccuracyCheck {
        -classifier: ImageClassifier
        -goal_percent: int
        -max_seconds: int
        +check_photo(photo, right_answer)
        +run(folder)
    }
    class Recommender {
        -adapter: LLMAdapter
        -advisor: RuleBasedAdvisor
        +recommend(product) AIPrediction
    }
    class LLMAdapter {
        -url: str
        -model: str
        -max_tokens: int
        -api_key: str
        +has_api_key() bool
        +ask(question) str
    }
    class RuleBasedAdvisor {
        -resale_minimum: int
        -repair_minimum: int
        -actions: list
        -version: str
        +check_product(product)
        +advise(product)
    }
    class AIPrediction {
        -action: str
        -reason: str
        -source: str
        -model: str
        -rating: int
        -created_at: str
        +rate(rating)
    }
    RecommendationService *-- RecommendationRepository
    RecommendationService *-- ImageClassifier
    RecommendationService *-- PhotoCheck
    RecommendationService ..> Recommender : creates
    RecommendationService ..> LLMAdapter : creates
    Recommender "1" o-- "0..1" LLMAdapter : asks first
    Recommender "1" *-- "1" RuleBasedAdvisor : falls back to
    Recommender ..> AIPrediction : creates
    RecommendationRepository ..> AIPrediction : stores and loads
    AccuracyCheck "1" --> "1" ImageClassifier : tests
```


### 2.3 Database

All four subsystems share one SQLite database, `database/passport.db`. The tables are defined in [database/schema.sql](database/schema.sql), and [database/connection.py](database/connection.py) creates them when the app starts. Set `PASSPORT_DB` to use another file; Docker uses `/data/passport.db`, and the tests use a temporary file.


| Table | Subsystem | What it holds |
| ----- | --------- | ------------- |
| `users` | 1. Passport | Email, role and salted password hash (never the password) |
| `sessions` | 1. Passport | Login sessions: SHA-256 of the token, user and expiry time |
| `products` | 1. Passport | UUID, name, model, category, lifespan, spare parts %, condition, owner, QR code address |
| `material_components` | 1. Passport | Each material of a product with its %, and whether it is recycled, recyclable or hazardous |
| `lifecycle_events` | 2. Event ledger | Each event with its time, who recorded it, details (JSON), previous hash and own hash |
| `circularity_scores` | 3. Score engine | Every score ever calculated: total, grade, five sub-scores (JSON), missing data and the reason, e.g. `event: repaired` |
| `ai_predictions` | 4. AI engine | Each recommendation: action, reason, source (LLM or rules), model and the user's rating (1–5) |
| `photo_identifications` | 4. AI engine | Each photo identification: category and material with their confidence, and the model used |


**Demo data:** On its first start, the app fills an empty database with synthetic data from [database/seed.py](database/seed.py): the 4 demo users and 100 products, each with materials, a lifecycle history from 2021 to 2025, scores and a recommendation. The data goes in through each subsystem's own service, so every rule is checked. A fixed random seed gives the same products every time.

```bash
python -m database.seed               # delete and recreate the database with 100 products
python -m database.seed --count 250   # with another number of products
```

The `/database` page shows every table with its rows, read live. The `.db` files are not committed to Git (see `.gitignore`).

## 3. Run it

Tested with Python 3.14. Run every command from the project folder.

### With Docker

```bash
docker compose up --build                  # without photo identification (small image)
INSTALL_CLIP=1 docker compose up --build   # with CLIP for photo identification (about 2 GB)
```

Open http://localhost:8000. Stop with `Ctrl+C` or `docker compose down`. The database is kept in a Docker volume, and the API key is read from `.env` when the container starts.

### Without Docker

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Open http://localhost:8000 for the pages and http://localhost:8000/docs for the API. On its first start, the app creates the database with demo data. To rebuild it, stop the app and run `python -m database.seed`.

### AI advice with KI:connect (optional)

Copy `.env.example` to `.env` and enter your key (`KICONNECT_API_KEY=...`). Without a key, the AI engine automatically uses its rules.

## 4. Demo Accounts and Pages

Reading passports is public. To register a product, record an event or get an AI recommendation, log in at `/login`. The demo accounts use the password `demo-password`.

| Email | May do |
| ----- | ------ |
| `admin@example.com` | Register products, edit any product, record every event type |
| `manufacturer@example.com` | Register products, edit its own products; record manufactured, sold, repaired, refurbished |
| `recycler@example.com` | Record refurbished, recycled |
| `consumer@example.com` | Record sold, used, repaired |

| Address | What it shows |
| ------- | ------------- |
| `/` | Search products, with their latest score and grade |
| `/login`, `/signup` | Log in, or create an account |
| `/register` | Register a product and its materials, optionally filled in from a photo |
| `/passport/{uuid}` | Product, QR code, score, lifecycle history, AI recommendation |
| `/passport/{uuid}/edit` | Change the product's name and model |
| `/database` | Every table with its rows, read live |
| `/api/products` | All products as JSON |
| `/api/passports/{uuid}`, `/events`, `/verify`, `/scores` | The passport, its event history, chain check and score history as JSON |

## 5. Error Handling

Each subsystem has an `errors.py` with one base class and smaller classes for each kind of problem, so other code can catch all errors of a subsystem with one `except`, or only one kind. Most classes also inherit from a built-in error (`ValueError`, `LookupError` or `PermissionError`), so the web app shows a clear message or a "Not found" page instead of crashing.

| Subsystem | Base class | Error classes |
| --------- | ---------- | ------------- |
| 1. Passport | `PassportError` | `AccountError`, `RegistrationError`, `ProductEditError`, `NotAllowedError`, `ProductNotFoundError` |
| 2. Event ledger | `LedgerError` | `ProductNotFoundError` (404), `EventNotPermittedError` (403), `InvalidEventError` (400), `InvalidEventOrderError` (409), `ChainConflictError` (409), `LedgerDatabaseError` (500). Each error carries its own message and HTTP status code. If the score engine fails after an event is saved, the failure is logged and the event is kept |
| 3. Score engine | `ScoreError` | `ProductNotFoundError`, `InvalidScoreDataError`, `InvalidConfigError` (and `ScoreErrorHandler`, which hides internal details) |
| 4. AI engine | `AIEngineError` | `ProductNotFoundError`, `InvalidProductError`, `InvalidPhotoError`, `InvalidRatingError`, `PredictionNotFoundError`, `LLMError` (caught by the `Recommender`, which then uses the rules) |

## 6. Tests

### All tests

```bash
python -m pytest -v                                 # 88 tests
```

### Each subsystem

Run one file with `python -m pytest tests/<file> -v`, for example `python -m pytest tests/test_subsystem1.py -v`.

| File | Tests | What they check |
| ---- | ----- | --------------- |
| `test_subsystem1.py` | 31 | Sign-up, login and roles; product registration with UUID, passport and QR code; materials total 100%; search; JSON export; password hashing; account lock; page speed; API documentation |
| `test_subsystem2.py` | 14 | Roles and event order; hash chain and tamper detection; same hash for same data; corrections as new events; concurrent events; speed; link to the score engine; error classes |
| `test_subsystem3_score.py` | 15 | Score and grade; the five sub-scores; missing data; score stays between 0 and 100; same result every time; score after a repair; score saved when a product is registered; error handling |
| `test_subsystem4_ai_engine.py` | 28 | Rules and LLM fallback; LLM reason; ratings; photo checks and identification; accuracy check; error handling |

### Test coverage

```bash
python -m pytest --cov                           # with test coverage
python -m pytest --cov --cov-report=html         # coverage as a web page: open htmlcov/index.html
```

The tests use a temporary database, so they never change `database/passport.db`. They replace the real LLM and CLIP with small fake classes, so they need no internet and no API key.

**Continuous integration:** GitHub Actions (`.github/workflows/tests.yml`) runs all tests with coverage on every push and pull request, and checks that the Docker image still builds. The badge at the top shows the latest result.

## 7. Class Documentation

Every class has docstrings. Each subsystem's classes, with their methods, getters and setters, can be read with `pydoc` (press `q` to close it):

```bash
python -m pydoc subsystem1_passport
python -m pydoc subsystem2_ledger
python -m pydoc subsystem3_score
python -m pydoc subsystem4_ai_engine
```

## 8. Limitations

- Runs locally over HTTP with SQLite, so it suits a demo, not many users at once.
- Demo data is synthetic, and the score weights are our own choice, not an official standard.
- Photo identification knows only 10 categories and 6 materials.
- AI advice from the LLM needs a KI:connect key and internet; otherwise the simpler rules are used.
