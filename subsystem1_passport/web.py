from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from . import repository as repo
from .security import COOKIE_NAME, create_token, get_db, optional_user

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
router = APIRouter(include_in_schema=False)

PAGE_SIZE = 20


def _render(request, name, context, status_code=200):
    return templates.TemplateResponse(request, name, context, status_code=status_code)


def _safe_next(target):
    return target if isinstance(target, str) and target.startswith("/") and not target.startswith("//") else "/"


def _to_login(request):
    return RedirectResponse(f"/login?next={quote(str(request.url.path))}", status_code=303)


def _number(text):
    text = (text or "").strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return text  # the domain class rejects it with a clear message


def parse_registration_form(form):
    data = {
        "name": (form.get("name") or "").strip(),
        "model": (form.get("model") or "").strip(),
        "category": (form.get("category") or "").strip(),
        "lifespan_years": _number(form.get("lifespan_years")),
        "spare_parts_percent": _number(form.get("spare_parts_percent")),
        "materials": [],
    }
    indexes = sorted({int(k.split("-")[1]) for k in form.keys()
                      if k.startswith("materials-") and k.split("-")[1].isdigit()})
    for i in indexes:
        material = (form.get(f"materials-{i}-material") or "").strip()
        percent = _number(form.get(f"materials-{i}-percent"))
        if not material and percent is None:
            continue  # empty row
        data["materials"].append({
            "material": material,
            "percent": percent,
            "recycled": _number(form.get(f"materials-{i}-recycled")) or 0,
            "recyclable": form.get(f"materials-{i}-recyclable") == "on",
            "hazard": form.get(f"materials-{i}-hazard") == "on",
        })
    return data


# ---------------------------------------------------------------- pages
@router.get("/")
def home():
    return RedirectResponse("/search", status_code=307)


@router.get("/search", response_class=HTMLResponse)
def search_page(request: Request, q: str = "", category: str = "", page: int = 1,
                db=Depends(get_db), user=Depends(optional_user)):
    page = max(page, 1)
    rows, total = repo.search_products(db, q, category, page, PAGE_SIZE)
    pages = max((total + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    return _render(request, "search.html", {
        "user": user, "q": q, "category": category, "rows": rows, "total": total,
        "page": page, "pages": pages, "categories": repo.list_categories(db)})


@router.get("/passport/{uuid}", response_class=HTMLResponse)
def passport_page(uuid: str, request: Request, db=Depends(get_db), user=Depends(optional_user)):
    try:
        row = repo.get_product(db, uuid)
    except repo.NotFound:
        return _render(request, "error.html", {"user": user, "title": "Passport not found",
                       "message": "No product has this UUID."}, 404)
    data = repo.passport_dict(row, request.app.state.settings.base_url)
    allowed_events = []
    if user is not None:
        allowed_events = [t for t in repo.EVENT_TYPES if user.role in repo.EVENT_PERMISSIONS[t]]
    return _render(request, "passport.html", {
        "user": user, "p": data, "allowed_events": allowed_events,
        "created": request.query_params.get("created") == "1",
        "error": request.query_params.get("error")})


@router.get("/passport/{uuid}/qr.png")
def passport_qr(uuid: str, request: Request, db=Depends(get_db)):
    try:
        row = repo.get_product(db, uuid)
    except repo.NotFound:
        return Response(status_code=404)
    qr = repo.get_qr_code(db, row, request.app.state.settings.base_url)
    download = request.query_params.get("download") == "1"
    headers = {"Cache-Control": "public, max-age=86400"}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="qr-{row.uuid}.png"'
    return Response(qr.png_bytes, media_type="image/png", headers=headers)


@router.post("/passport/{uuid}/events")
async def passport_add_event(uuid: str, request: Request, db=Depends(get_db),
                             user=Depends(optional_user)):
    if user is None:
        return _to_login(request)
    form = await request.form()
    try:
        row = repo.get_product(db, uuid)
        repo.add_lifecycle_event(db, row, user, form.get("event_type", ""), form.get("details", ""))
    except repo.NotFound:
        return Response(status_code=404)
    except (ValueError, PermissionError) as err:
        return RedirectResponse(f"/passport/{uuid}?error={quote(str(err))}#history", status_code=303)
    return RedirectResponse(f"/passport/{uuid}#history", status_code=303)


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, db=Depends(get_db), user=Depends(optional_user)):
    if user is None:
        return _to_login(request)
    if not repo.to_user(user).can("register_product"):
        return _render(request, "error.html", {"user": user, "title": "Not allowed",
                       "message": "Only manufacturers and admins can register products."}, 403)
    return _render(request, "register.html", {"user": user, "values": None, "errors": [],
                                              "missing": [], "categories": repo.list_categories(db)})


@router.post("/register", response_class=HTMLResponse)
async def register_submit(request: Request, db=Depends(get_db), user=Depends(optional_user)):
    if user is None:
        return _to_login(request)
    data = parse_registration_form(await request.form())
    try:
        row = repo.register_product(db, data, user, request.app.state.settings.base_url)
    except repo.IncompleteRegistration as err:
        errors, missing, code = [str(err)], err.missing, 422
    except repo.Forbidden as err:
        errors, missing, code = [str(err)], [], 403
    except (ValueError, TypeError) as err:
        errors, missing, code = [str(err)], [], 422
    else:
        return RedirectResponse(f"/passport/{row.uuid}?created=1", status_code=303)
    db.rollback()
    return _render(request, "register.html", {"user": user, "values": data, "errors": errors,
                   "missing": missing, "categories": repo.list_categories(db)}, code)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str = "/", user=Depends(optional_user)):
    return _render(request, "login.html", {"user": user, "next": _safe_next(next), "error": None,
                                           "mode": "login", "email": ""})


@router.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, db=Depends(get_db)):
    form = await request.form()
    next_url = _safe_next(form.get("next", "/"))
    row = repo.authenticate(db, form.get("email", ""), form.get("password", ""))
    if row is None:
        return _render(request, "login.html", {"user": None, "next": next_url, "mode": "login",
                       "error": "Wrong email or password.", "email": form.get("email", "")}, 401)
    return _logged_in(request, row, next_url)


@router.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request, next: str = "/", user=Depends(optional_user)):
    return _render(request, "login.html", {"user": user, "next": _safe_next(next), "error": None,
                                           "mode": "signup", "email": ""})


@router.post("/signup", response_class=HTMLResponse)
async def signup_submit(request: Request, db=Depends(get_db)):
    form = await request.form()
    next_url = _safe_next(form.get("next", "/"))
    try:
        row = repo.create_user(db, form.get("email", ""), form.get("password", ""), "consumer")
    except ValueError as err:
        return _render(request, "login.html", {"user": None, "next": next_url, "mode": "signup",
                       "error": str(err), "email": form.get("email", "")}, 422)
    return _logged_in(request, row, next_url)


def _logged_in(request, row, next_url):
    settings = request.app.state.settings
    response = RedirectResponse(next_url, status_code=303)
    response.set_cookie(COOKIE_NAME, create_token(row.id, settings.secret_key, settings.token_ttl_seconds),
                        max_age=settings.token_ttl_seconds, httponly=True, samesite="lax",
                        secure=settings.base_url.startswith("https://"))
    return response


@router.post("/logout")
def logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response
