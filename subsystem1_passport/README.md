# Subsystem 1: Passport, QR code and web UI

Owner: Mosaddeka Mallick · Tech: FastAPI + SQLite (`sqlite3`) + Jinja2

## Run it

From the project folder (one level up), after `pip install -r requirements.txt`:

```bash
python -m subsystem1_passport.seed
```

```bash
uvicorn subsystem1_passport.app:create_app --factory --reload
```

- Web UI: http://localhost:8000 (search → passport page; log in to register products)
- API docs (OpenAPI): http://localhost:8000/docs and http://localhost:8000/redoc

The seed script creates four demo logins (password `demo-pass-123`) and 100 synthetic products:

| Role         | Email               |
| ------------ | ------------------- |
| admin        | admin@demo.local    |
| manufacturer | maker@demo.local    |
| recycler     | recycler@demo.local |
| consumer     | consumer@demo.local |

Load test with 10,000 products: `python -m subsystem1_passport.seed --count 10000`.

Settings (environment variables):

| Variable                         | Default                 | Meaning                                                       |
| -------------------------------- | ----------------------- | ------------------------------------------------------------- |
| `SECRET_KEY`                     | random per start        | Signs login tokens. Set it, or logins end on every restart.   |
| `PUBLIC_BASE_URL`                | `http://localhost:8000` | Address printed in QR codes. Use the real address for labels. |
| `DATABASE_PATH`                  | `passport.db`           | SQLite file.                                                  |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | –                       | Creates this admin account on start if it does not exist.     |

## Tests

Unit tests follow in Homework Assignment 4.

## Files

| File                                                                          | What it does                                                                                              |
| ----------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `user.py`, `product.py`, `material_component.py`, `passport.py`, `qr_code.py` | The five classes from the class diagram. All validation rules live here.                                  |
| `database.py`                                                                 | SQLite schema (`users`, `products`, `material_components`, `qr_codes`, `history_events`) and connections. |
| `models.py`                                                                   | Plain records for database rows.                                                                          |
| `repository.py`                                                               | Service layer: SQL, converting rows into the five classes, links to Subsystems 2 and 3.                   |
| `api.py`, `schemas.py`                                                        | REST API (JSON) and its request and response models.                                                      |
| `web.py`, `templates/`, `static/`                                             | Web screens: search, public passport page, registration form, login.                                      |
| `security.py`                                                                 | Signed login tokens (Bearer header for the API, HttpOnly cookie for the web pages).                       |
| `app.py`                                                                      | Builds the FastAPI app.                                                                                   |
| `seed.py`                                                                     | Demo users and synthetic products.                                                                        |

## Requirements

| #     | Functional requirement                                | Where                                                     |
| ----- | ----------------------------------------------------- | --------------------------------------------------------- |
| FR 1  | Register product: name, category, materials, lifespan | `POST /api/products`, `/register` form                    |
| FR 2  | Unique UUID for every product                         | `Product.initialize` (uuid4), `UNIQUE` column             |
| FR 3  | QR code linking to the passport page                  | `QRCode`, stored in `qr_codes`, `/passport/{uuid}/qr.png` |
| FR 4  | Passport page on scan, no login                       | `GET /passport/{uuid}`                                    |
| FR 5  | Material percentages sum to 100 %                     | `Product.materials_valid`, live total in the form         |
| FR 6  | Reject incomplete registrations, name missing fields  | `Product.missing_in` → 422 with `missing_fields`          |
| FR 7  | Search by UUID, name or category                      | `GET /api/products?q=`, `/search`                         |
| FR 8  | Four roles with permissions                           | `User.ROLES`, `User.PERMISSIONS`                          |
| FR 9  | Score and history on the page                         | Subsystem 3 score + hash-chained history                  |
| FR 10 | Export passport as JSON via REST                      | `GET /api/products/{uuid}`, `/export` (file download)     |

| #      | Non-functional requirement          | How                                                                                        |
| ------ | ----------------------------------- | ------------------------------------------------------------------------------------------ |
| NFR 1  | Page loads in under 2 s             | Server-rendered HTML, stored QR. About 15 ms measured with 10,000 products                 |
| NFR 2  | 10,000 products without slowdown    | Indexes, pagination, checked with 10,000 seeded products (`seed --count 10000`)            |
| NFR 3  | Usable from 360 px                  | Mobile-first CSS, checked at 360 px with no sideways scrolling                             |
| NFR 4  | Register in under 3 minutes         | One form, category suggestions, live material total, input kept on errors                  |
| NFR 5  | bcrypt, login to edit               | `User.set_password` (bcrypt, cost 12), `require_user` on every write                       |
| NFR 6  | QR readable at 2 × 2 cm             | Error correction level Q, about 0.4 mm per module at 2 cm                                  |
| NFR 7  | UUIDs never reused, no hard deletes | No `DELETE` endpoint, archive instead; database triggers block deletes and history changes |
| NFR 8  | JSON with standard HTTP codes       | 200/201/401/403/404/409/422, `{"detail": ...}` bodies                                      |
| NFR 9  | OpenAPI docs                        | `/docs`, `/redoc`, `/openapi.json`                                                         |
| NFR 10 | 70 % test coverage                  | Homework Assignment 4                                                                      |
