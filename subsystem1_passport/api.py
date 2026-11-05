"""REST API (JSON, standard HTTP status codes - NFR 8). Documented at /docs and /redoc (NFR 9)."""
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from . import repository as repo
from .schemas import (Credentials, ErrorOut, EventIn, HistoryEventOut, NewUser, PassportOut,
                      ProductIn, ProductUpdate, RoleChange, SearchResult, TokenOut, UserOut)
from .security import create_token, get_db, require_user

ERRORS = {
    401: {"model": ErrorOut, "description": "Login required"},
    403: {"model": ErrorOut, "description": "Your role does not allow this"},
    404: {"model": ErrorOut, "description": "Product not found"},
    409: {"model": ErrorOut, "description": "Conflict (e.g. email taken, product archived)"},
    422: {"model": ErrorOut, "description": "Invalid or incomplete input"},
}

router = APIRouter(prefix="/api")


def _base_url(request: Request):
    return request.app.state.settings.base_url


def _user_out(row):
    return UserOut(email=row.email, role=row.role)


# ---------------------------------------------------------------- auth & users
@router.post("/auth/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED,
             tags=["auth"], responses={409: ERRORS[409], 422: ERRORS[422]})
def signup(body: Credentials, db=Depends(get_db)):
    """Create a consumer account. Other roles are given by an admin."""
    return _user_out(repo.create_user(db, body.email, body.password, "consumer"))


def _token_for(request, row):
    settings = request.app.state.settings
    return TokenOut(access_token=create_token(row.id, settings.secret_key, settings.token_ttl_seconds),
                    role=row.role)


@router.post("/auth/login", response_model=TokenOut, tags=["auth"], responses={401: ERRORS[401]})
def login(body: Credentials, request: Request, db=Depends(get_db)):
    """Log in with JSON. Send the token as `Authorization: Bearer <token>`."""
    row = repo.authenticate(db, body.email, body.password)
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password.",
                            headers={"WWW-Authenticate": "Bearer"})
    return _token_for(request, row)


@router.post("/auth/token", response_model=TokenOut, tags=["auth"], responses={401: ERRORS[401]})
def login_form(request: Request, form: OAuth2PasswordRequestForm = Depends(),
               db=Depends(get_db)):
    """Same as /auth/login, as a form (username = email). Used by the Authorize button in /docs."""
    return login(Credentials(email=form.username, password=form.password), request, db)


@router.get("/users/me", response_model=UserOut, tags=["users"], responses={401: ERRORS[401]})
def me(user=Depends(require_user)):
    return _user_out(user)


@router.get("/users", response_model=list[UserOut], tags=["users"],
            responses={401: ERRORS[401], 403: ERRORS[403]})
def users(user=Depends(require_user), db=Depends(get_db)):
    """Admin only."""
    if not repo.to_user(user).can("manage_users"):
        raise repo.Forbidden("Only an admin can list users.")
    return [_user_out(r) for r in repo.list_users(db)]


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED, tags=["users"],
             responses={401: ERRORS[401], 403: ERRORS[403], 409: ERRORS[409], 422: ERRORS[422]})
def create_user(body: NewUser, user=Depends(require_user), db=Depends(get_db)):
    """Admin only: create an account with any of the four roles (FR 8)."""
    if not repo.to_user(user).can("manage_users"):
        raise repo.Forbidden("Only an admin can create accounts with a role.")
    return _user_out(repo.create_user(db, body.email, body.password, body.role))


@router.patch("/users/{email}/role", response_model=UserOut, tags=["users"],
              responses={401: ERRORS[401], 403: ERRORS[403], 404: ERRORS[404], 422: ERRORS[422]})
def change_role(email: str, body: RoleChange, user=Depends(require_user), db=Depends(get_db)):
    """Admin only."""
    return _user_out(repo.set_user_role(db, user, email, body.role))


# ---------------------------------------------------------------- products
@router.post("/products", response_model=PassportOut, status_code=status.HTTP_201_CREATED,
             tags=["products"], responses={k: ERRORS[k] for k in (401, 403, 422)})
def register(body: ProductIn, request: Request, response: Response,
             user=Depends(require_user), db=Depends(get_db)):
    """FR 1-3, 5, 6: register a product. Returns its passport with a new UUID and QR code URL."""
    row = repo.register_product(db, body.model_dump(), user, _base_url(request))
    response.headers["Location"] = f"/api/products/{row.uuid}"
    return repo.passport_dict(row, _base_url(request))


@router.get("/products", response_model=SearchResult, tags=["products"])
def search(request: Request, q: str = "", category: str = "",
           page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=repo.MAX_PAGE_SIZE),
           include_archived: bool = False, db=Depends(get_db)):
    """FR 7: search by UUID (or its first characters), name or category. No login needed."""
    rows, total = repo.search_products(db, q, category, page, page_size, include_archived)
    base = _base_url(request).rstrip("/")
    return SearchResult(total=total, page=page, page_size=page_size, items=[
        {"uuid": r.uuid, "name": r.name, "model": r.model, "category": r.category,
         "archived": r.archived, "public_url": f"{base}/passport/{r.uuid}"} for r in rows])


@router.get("/products/{uuid}", response_model=PassportOut, tags=["products"],
            responses={404: ERRORS[404]})
def passport(uuid: str, request: Request, db=Depends(get_db)):
    """FR 4, 9, 10: the full passport as JSON, with score and history. No login needed."""
    return repo.passport_dict(repo.get_product(db, uuid), _base_url(request))


@router.get("/products/{uuid}/export", tags=["products"], responses={
    200: {"content": {"application/json": {}}, "description": "Passport JSON file"}, 404: ERRORS[404]})
def export(uuid: str, request: Request, db=Depends(get_db)):
    """FR 10: download the passport as a .json file."""
    data = repo.passport_dict(repo.get_product(db, uuid), _base_url(request))
    return Response(json.dumps(data, indent=2), media_type="application/json", headers={
        "Content-Disposition": f'attachment; filename="passport-{data["uuid"]}.json"'})


@router.get("/products/{uuid}/qr.png", tags=["products"], responses={
    200: {"content": {"image/png": {}}, "description": "QR code image"}, 404: ERRORS[404]})
def qr_png(uuid: str, request: Request, db=Depends(get_db)):
    """FR 3: the QR code that opens the public passport page."""
    qr = repo.get_qr_code(db, repo.get_product(db, uuid), _base_url(request))
    return Response(qr.png_bytes, media_type="image/png",
                    headers={"Cache-Control": "public, max-age=86400"})


@router.patch("/products/{uuid}", response_model=PassportOut, tags=["products"],
              responses={k: ERRORS[k] for k in (401, 403, 404, 409, 422)})
def update(uuid: str, body: ProductUpdate, request: Request,
           user=Depends(require_user), db=Depends(get_db)):
    """Change product data (owner or admin). The UUID stays the same."""
    row = repo.get_product(db, uuid)
    data = body.model_dump(exclude_unset=True)
    if "materials" in data and data["materials"] is not None:
        data["materials"] = [m.model_dump() for m in body.materials]
    row = repo.update_product(db, row, data, user)
    return repo.passport_dict(row, _base_url(request))


@router.post("/products/{uuid}/archive", response_model=PassportOut, tags=["products"],
             responses={k: ERRORS[k] for k in (401, 403, 404)})
def archive(uuid: str, request: Request, user=Depends(require_user), db=Depends(get_db)):
    """NFR 7: products are never deleted. An admin can archive one instead."""
    row = repo.archive_product(db, repo.get_product(db, uuid), user)
    return repo.passport_dict(row, _base_url(request))


@router.post("/products/{uuid}/events", response_model=HistoryEventOut,
             status_code=status.HTTP_201_CREATED, tags=["products"],
             responses={k: ERRORS[k] for k in (401, 403, 404, 409, 422)})
def add_event(uuid: str, body: EventIn, user=Depends(require_user), db=Depends(get_db)):
    """Add a lifecycle event. Who may add which event follows Subsystem 2's rules."""
    event = repo.add_lifecycle_event(db, repo.get_product(db, uuid), user, body.event_type, body.details)
    return event.to_dict(public=True)
