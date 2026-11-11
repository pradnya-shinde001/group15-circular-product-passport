"""The web app: HTML pages and a small JSON API, built with FastAPI.
It has no business rules and no SQL: every page asks one of the four subsystems.

Run from the project folder:  uvicorn app:app --reload
Then open:  http://localhost:8000        (web pages)
            http://localhost:8000/docs   (API documentation)"""
import os
import tempfile
import threading
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from database import table_names, table_rows
from database.seed import ensure_demo_data
from subsystem1_passport.auth_service import SIGNUP_ROLES, AuthService
from subsystem1_passport.passport_service import (
    CONDITIONS,
    REGISTER_ROLES,
    PassportService,
)
from subsystem2_ledger.errors import LedgerError
from subsystem2_ledger.ledger_service import EVENT_PERMISSIONS, LedgerService
from subsystem3_score.score_service import ScoreService
from subsystem3_score.score_weights import ScoreWeights
from subsystem4_ai_engine.errors import InvalidPhotoError, InvalidRatingError
from subsystem4_ai_engine.image_classifier import RECYCLABLE_MATERIALS
from subsystem4_ai_engine.recommendation_service import RecommendationService

# ---------- 1. Setup ----------

MATERIAL_ROWS = 5            # how many material lines the register form shows
SESSION_COOKIE = "session"   # the name of the login cookie in the browser
CATEGORIES = list(ScoreWeights().category_lifespans)  # the categories the score engine knows

# One object for each subsystem.
# A new product or a new event tells the score engine to calculate a new score.
scores = ScoreService()
passports = PassportService(on_registered=scores.on_registered)
ledger = LedgerService(on_event=scores.on_event)
advice = RecommendationService()
auth = AuthService()

# Create the tables, and add the demo data when the database is still empty.
ensure_demo_data()


def preload_clip():
    """Load the CLIP model now, so the first uploaded photo does not wait for it (Subsystem 4, NFR 2)."""
    try:
        advice.get_classifier().load()
    except ImportError:
        print("CLIP is not loaded: install torch and transformers to identify photos.")


# A background thread, so the pages work at once while CLIP loads. The tests set PRELOAD_CLIP=0.
if os.environ.get("PRELOAD_CLIP", "1") == "1":
    threading.Thread(target=preload_clip, daemon=True).start()

app = FastAPI(title="Circular Product Passport")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


# ---------- 2. Helpers ----------

def get_user(request):
    """The logged-in user as a dict (id, email, role), or None when nobody is logged in."""
    token = request.cookies.get(SESSION_COOKIE)
    return auth.user_for_token(token)


def show(request, template, data, status_code=200):
    """Show an HTML page. Every page also gets the logged-in user, for the menu."""
    user = get_user(request)
    data["user"] = user
    data["can_register"] = user is not None and user["role"] in REGISTER_ROLES
    return templates.TemplateResponse(request, template, data, status_code=status_code)


def go_to(url):
    """Send the browser to another page."""
    return RedirectResponse(url, status_code=303)


def logged_in_response(token, next):
    """Set the login cookie and go to `next`, but only to a page of this app, never another website."""
    if not next.startswith("/") or next.startswith("//"):
        next = "/"
    response = go_to(next)
    secure = os.environ.get("PASSPORT_BASE_URL", "").startswith("https://")  # HTTPS only once deployed
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", secure=secure)
    return response


def to_number(text, label, errors):
    """Turn the text from a form field into a number.
    If that is not possible, add a message to `errors` and return None."""
    try:
        return float(text)
    except (TypeError, ValueError):
        errors.append(f"{label} must be a number.")
        return None


@app.exception_handler(LookupError)
def not_found(request: Request, error: LookupError):
    """The subsystems raise LookupError for an unknown product. Show 'Not found' instead of crashing."""
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": str(error)}, status_code=404)
    return show(request, "message.html", {"title": "Not found", "text": str(error)}, 404)


# ---------- 3. Login and logout ----------

@app.get("/login")
def login_page(request: Request, next: str = "/"):
    return show(request, "login.html", {"next": next, "email": ""})


@app.post("/login")
def login(request: Request, email: str = Form(""), password: str = Form(""), next: str = Form("/")):
    try:
        user, token = auth.login(email, password)
    except ValueError as error:
        data = {"next": next, "email": email, "errors": [str(error)]}
        # 401 for a wrong email or password, 429 after too many wrong passwords
        return show(request, "login.html", data, getattr(error, "status_code", 401))
    return logged_in_response(token, next)


@app.get("/signup")
def signup_page(request: Request, next: str = "/"):
    if get_user(request) is not None:
        return go_to("/")
    return show(request, "signup.html", {"next": next, "email": "", "role": "consumer", "roles": SIGNUP_ROLES})


@app.post("/signup")
def signup(request: Request, email: str = Form(""), password: str = Form(""),
           role: str = Form("consumer"), next: str = Form("/")):
    try:
        user, token = auth.sign_up(email, password, role)
    except ValueError as error:
        data = {"next": next, "email": email, "role": role, "roles": SIGNUP_ROLES, "errors": [str(error)]}
        return show(request, "signup.html", data, 400)
    return logged_in_response(token, next)


@app.post("/logout")
def logout(request: Request):
    auth.logout(request.cookies.get(SESSION_COOKIE))
    response = go_to("/")
    response.delete_cookie(SESSION_COOKIE)
    return response


# ---------- 4. Search page ----------

@app.get("/")
def home(request: Request, q: str = ""):
    products = passports.search(q)
    return show(request, "home.html", {"q": q, "products": products})


# ---------- 5. Register a product (manufacturer or admin only) ----------

def register_form_data(form, errors):
    """What the register page needs: the values typed so far and any error messages."""
    return {"form": form, "errors": errors, "categories": CATEGORIES,
            "conditions": CONDITIONS, "rows": range(MATERIAL_ROWS)}


def not_allowed_page(request, user):
    text = f"Only a manufacturer or an admin can register a product. You are logged in as a {user['role']}."
    return show(request, "message.html", {"title": "Not allowed", "text": text}, 403)


@app.get("/register")
def register_page(request: Request):
    user = get_user(request)
    if user is None:
        return go_to("/login?next=/register")
    if user["role"] not in REGISTER_ROLES:
        return not_allowed_page(request, user)
    return show(request, "register.html", register_form_data({}, []))


@app.post("/register")
async def register(request: Request):
    user = get_user(request)
    if user is None:
        return go_to("/login?next=/register")
    if user["role"] not in REGISTER_ROLES:
        return not_allowed_page(request, user)

    form = dict(await request.form())
    errors = []
    lifespan = to_number(form.get("lifespan_years"), "Lifespan", errors)
    spare_parts = to_number(form.get("spare_parts_percent"), "Spare parts", errors)

    # Read the material rows. Rows without a material name are skipped.
    materials = []
    for i in range(MATERIAL_ROWS):
        name = form.get(f"material_{i}", "").strip()
        if name == "":
            continue
        percent = to_number(form.get(f"percent_{i}"), f"Percent of {name}", errors)
        materials.append({
            "material": name,
            "percent": percent,
            "recycled": f"recycled_{i}" in form,      # a ticked checkbox is sent, an empty one is not
            "recyclable": f"recyclable_{i}" in form,
            "hazard": f"hazard_{i}" in form,
        })

    if len(errors) == 0:
        try:
            uuid = passports.register_product(form.get("name", ""), form.get("category", ""), lifespan,
                                              form.get("model", ""), user["id"], spare_parts,
                                              form.get("condition", ""), materials)
            return go_to(f"/passport/{uuid}?msg=Product+registered")
        except ValueError as error:
            errors = error.args[0]  # Subsystem 1 lists every problem it found

    return show(request, "register.html", register_form_data(form, errors), 400)


@app.post("/register/photo")
async def register_from_photo(request: Request, photo: UploadFile = File(...)):
    """Subsystem 4: guess the category and the main material from a photo, and pre-fill the form."""
    user = get_user(request)
    if user is None:
        return go_to("/login?next=/register")
    if user["role"] not in REGISTER_ROLES:
        return not_allowed_page(request, user)

    # Save the upload to a temporary file. identify_photo() checks it and deletes it afterwards.
    suffix = Path(photo.filename or "").suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
        temp_file.write(await photo.read())

    try:
        result = advice.identify_photo(temp_file.name)
    except InvalidPhotoError as error:
        return show(request, "register.html", register_form_data({}, [str(error)]), 400)

    # Only a guess that is not uncertain goes into the form; the user can still change it.
    form = {}
    best_category = result["categories"][0]
    best_material = result["materials"][0]
    if not best_category["uncertain"]:
        form["category"] = best_category["label"]
        form["lifespan_years"] = ScoreWeights().category_lifespans.get(best_category["label"], "")
    if not best_material["uncertain"]:
        form["material_0"] = best_material["label"]
        if best_material["label"] in RECYCLABLE_MATERIALS:
            form["recyclable_0"] = "on"  # tick "Recyclable", so the score does not miss it

    data = register_form_data(form, [])
    data["photo_result"] = result
    data["matches"] = passports.search(best_category["label"])[:5]  # existing passports of the same kind
    return show(request, "register.html", data)


# ---------- 6. Passport page ----------

def passport_page_data(uuid, message, errors):
    """Everything the passport page shows, collected from the four subsystems."""
    events = ledger.history(uuid)
    repairs = 0
    for event in events:
        if event["event_type"] == "repaired":
            repairs = repairs + 1

    return {
        "product": passports.get_product(uuid),        # Subsystem 1
        "materials": passports.materials(uuid),
        "events": events,                              # Subsystem 2
        "repairs": repairs,
        "chain": ledger.verify(uuid),                  # Subsystem 2
        "permissions": EVENT_PERMISSIONS,
        "next_events": ledger.next_events(uuid),       # Subsystem 2
        "score": scores.latest(uuid),                  # Subsystem 3
        "score_history": scores.history(uuid),
        "predictions": advice.history(uuid),           # Subsystem 4
        "message": message,
        "errors": errors,
    }


@app.get("/passport/{uuid}")
def passport_page(request: Request, uuid: str, msg: str = ""):
    return show(request, "passport.html", passport_page_data(uuid, msg, []))


def edit_page_data(product, name, model, errors):
    """What the edit page needs: the product, the values typed so far and any error messages."""
    return {"product": product, "name": name, "model": model, "errors": errors}


@app.get("/passport/{uuid}/edit")
def edit_page(request: Request, uuid: str):
    user = get_user(request)
    if user is None:
        return go_to(f"/login?next=/passport/{uuid}/edit")
    product = passports.get_product(uuid)  # "Not found" for an unknown product
    if not passports.can_edit(product, user):
        text = "Only the manufacturer who registered this product, or an admin, can edit it."
        return show(request, "message.html", {"title": "Not allowed", "text": text}, 403)
    return show(request, "edit.html", edit_page_data(product, product["name"], product["model"], []))


@app.post("/passport/{uuid}/edit")
def edit_product(request: Request, uuid: str, name: str = Form(""), model: str = Form("")):
    user = get_user(request)
    if user is None:
        return go_to(f"/login?next=/passport/{uuid}/edit")
    product = passports.get_product(uuid)  # "Not found" for an unknown product
    try:
        passports.update_details(uuid, user, name, model)
    except PermissionError as error:
        return show(request, "message.html", {"title": "Not allowed", "text": str(error)}, 403)
    except ValueError as error:
        return show(request, "edit.html", edit_page_data(product, name, model, error.args[0]), 400)
    return go_to(f"/passport/{uuid}?msg=Details+updated")


@app.get("/passport/{uuid}/qr.png")
def qr_code(uuid: str):
    """The QR code image that opens this passport page."""
    return Response(passports.qr_png(uuid), media_type="image/png")


@app.post("/passport/{uuid}/events")
def add_event(request: Request, uuid: str, event_type: str = Form(...), note: str = Form("")):
    user = get_user(request)
    if user is None:
        return go_to(f"/login?next=/passport/{uuid}")

    try:
        ledger.add_event(uuid, user["id"], event_type, note)  # recorded by the logged-in user
    except LedgerError as error:  # 400, 403, 404, 409 or 500, each error brings its own status code
        errors = error.message if isinstance(error.message, list) else [str(error)]
        return show(request, "passport.html", passport_page_data(uuid, "", errors), error.status_code)

    return go_to(f"/passport/{uuid}?msg=Event+added#history")


@app.post("/passport/{uuid}/advice")
def ask_for_advice(request: Request, uuid: str):
    if get_user(request) is None:  # each request may call the paid LLM, so a login is needed
        return go_to(f"/login?next=/passport/{uuid}")
    prediction = advice.recommend(uuid)
    return go_to(f"/passport/{uuid}?msg=Recommendation:+{prediction.get_action()}#advice")


@app.post("/passport/{uuid}/advice/{prediction_id}/rate")
def rate_advice(request: Request, uuid: str, prediction_id: int, rating: int = Form(...)):
    try:
        advice.rate(prediction_id, rating)
    except InvalidRatingError as error:
        return show(request, "passport.html", passport_page_data(uuid, "", [str(error)]), 400)
    return go_to(f"/passport/{uuid}?msg=Thank+you+for+your+rating#advice")


# ---------- 7. Database page: every table, read live (admin only) ----------

@app.get("/database")
def database_page(request: Request, table: str = "products"):
    user = get_user(request)
    if user is None:
        return go_to("/login?next=/database")
    if user["role"] != "admin":
        text = "Only an admin can see the database tables."
        return show(request, "message.html", {"title": "Not allowed", "text": text}, 403)

    # The login sessions are private, so that table is never shown.
    tables = []
    for name in table_names():
        if name != "sessions":
            tables.append(name)
    if table not in tables:
        table = "products"

    columns, rows = table_rows(table)

    # Password hashes are never shown either.
    if "password_hash" in columns:
        position = columns.index("password_hash")
        safe_rows = []
        for row in rows:
            row = list(row)
            row[position] = "(hidden)"
            safe_rows.append(row)
        rows = safe_rows

    data = {"tables": tables, "table": table, "columns": columns, "rows": rows}
    return show(request, "database.html", data)


# ---------- 8. JSON API ----------

@app.get("/api/products")
def api_products(q: str = ""):
    """Search products by name, model, category or UUID."""
    return passports.search(q)


@app.get("/api/passports/{uuid}")
def api_passport(uuid: str):
    """The whole passport as JSON."""
    passport = passports.get_product(uuid)
    passport["materials"] = passports.materials(uuid)
    passport["score"] = scores.latest(uuid)
    passport["events"] = ledger.history(uuid)
    passport["chain"] = ledger.verify(uuid)
    passport["recommendations"] = advice.history(uuid)
    return passport

@app.get("/api/passports/{uuid}/events")
def api_events(uuid: str):
    """The event history of this product, oldest first."""
    passports.get_product(uuid)  # 404 for an unknown product
    return ledger.history(uuid)


@app.get("/api/passports/{uuid}/verify")
def api_verify(uuid: str):
    """Whether the event history is intact."""
    passports.get_product(uuid)  # 404 for an unknown product
    return ledger.verify(uuid)


@app.get("/api/passports/{uuid}/scores")
def api_scores(uuid: str):
    """Every score of this product, oldest first."""
    passports.get_product(uuid)  # 404 for an unknown product
    return scores.history(uuid)
