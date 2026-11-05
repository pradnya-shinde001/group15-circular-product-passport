import sqlite3
from datetime import datetime, timezone

from subsystem2_ledger import ChainVerifier, EventHasher
from subsystem2_ledger.event_ledger import EventLedger
from subsystem2_ledger.lifecycle_event import LifecycleEvent
from subsystem3_score import ScoreCalculator

from .material_component import MaterialComponent
from .models import HistoryEventRow, MaterialRow, ProductRow, QRCodeRow, UserRow
from .passport import Passport
from .product import Product
from .user import User

GENESIS_HASH = EventLedger.GENESIS_HASH
EVENT_TYPES = list(LifecycleEvent.EVENT_TYPES)
EVENT_PERMISSIONS = EventLedger.EVENT_PERMISSIONS
MAX_PAGE_SIZE = 100

_hasher = EventHasher()
_score_calculator = ScoreCalculator()


# ---------------------------------------------------------------- errors
class IncompleteRegistration(ValueError):

    def __init__(self, missing):
        self.missing = list(missing)
        super().__init__("Registration incomplete, missing: " + ", ".join(self.missing))


class NotFound(LookupError):
    pass


class Conflict(ValueError):
    pass


class Forbidden(PermissionError):
    pass


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


# ---------------------------------------------------------------- users
def to_user(row):
    return User(row.email, role=row.role, password_hash=row.password_hash)


def get_user(db, user_id):
    r = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return UserRow.from_db(r) if r else None


def _user_by_email(db, email):
    r = db.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()
    return UserRow.from_db(r) if r else None


def create_user(db, email, password, role="consumer"):
    user = User(email, role=role, password=password)  # validates email, role, password
    try:
        cur = db.execute("INSERT INTO users (email, role, password_hash, created_at) VALUES (?, ?, ?, ?)",
                         (user.get_email(), user.get_role(), user.get_password_hash(), _now_iso()))
    except sqlite3.IntegrityError:
        db.rollback()
        raise Conflict("An account with this email already exists.") from None
    db.commit()
    return get_user(db, cur.lastrowid)


def authenticate(db, email, password):
    if not isinstance(email, str):
        return None
    row = _user_by_email(db, email)
    if row is None or not row.active or not to_user(row).check_password(password):
        return None
    return row


def set_user_role(db, admin_row, target_email, role):
    if not to_user(admin_row).can("manage_users"):
        raise Forbidden("Only an admin can change roles.")
    row = _user_by_email(db, target_email)
    if row is None:
        raise NotFound("User not found.")
    user = to_user(row)
    user.set_role(role)  # validates the role
    db.execute("UPDATE users SET role = ? WHERE id = ?", (user.get_role(), row.id))
    db.commit()
    return get_user(db, row.id)


def list_users(db):
    return [UserRow.from_db(r) for r in db.execute("SELECT * FROM users ORDER BY id")]


# ---------------------------------------------------------------- products
def build_product(data, uuid=None):
    missing = Product.missing_in(data)
    if missing:
        raise IncompleteRegistration(missing)
    product = Product(
        data["name"], data["category"], data["lifespan_years"],
        model=data.get("model") or "",
        spare_parts_percent=data.get("spare_parts_percent"),
        uuid=uuid,
    )
    for i, m in enumerate(data["materials"], start=1):
        if not m.get("material"):
            raise IncompleteRegistration([f"materials[{i}].material"])
        if m.get("percent") in (None, ""):
            raise IncompleteRegistration([f"materials[{i}].percent"])
        product.add_material(MaterialComponent(
            m["material"], m["percent"],
            recycled=m.get("recycled", 0) or 0,
            hazard=m.get("hazard", False),
            recyclable=m.get("recyclable", True),
        ))
    product.validate()  # FR 5: percentages must sum to 100 %
    return product


def to_product(row):
    product = Product(row.name, row.category, row.lifespan_years, model=row.model,
                      spare_parts_percent=row.spare_parts_percent, uuid=row.uuid)
    for m in row.materials:
        product.add_material(MaterialComponent(m.material, m.percent, recycled=m.recycled_share,
                                               hazard=m.hazard, recyclable=m.recyclable))
    return product


def _insert_materials(db, product_id, product):
    db.executemany(
        "INSERT INTO material_components (product_id, material, percent, recycled_share, recyclable, hazard) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [(product_id, m.get_material(), m.get_percent(), m.get_recycled_share(), int(m.is_recyclable()),
          int(m.is_hazard())) for m in product.get_materials()])


def insert_product(db, product, owner_row):
    now = _now_iso()
    cur = db.execute(
        "INSERT INTO products (uuid, name, model, category, lifespan_years, spare_parts_percent, owner_id, "
        "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (product.get_uuid(), product.get_name(), product.get_model(), product.get_category(),
         product.get_lifespan_years(), product.get_spare_parts_percent(), owner_row.id, now, now))
    _insert_materials(db, cur.lastrowid, product)
    row = ProductRow(cur.lastrowid, product.get_uuid(), product.get_name(), product.get_model(),
                     product.get_category(), product.get_lifespan_years(), product.get_spare_parts_percent(),
                     owner_row.id, False, now)
    row.materials = [MaterialRow(m.get_material(), m.get_percent(), m.get_recycled_share(),
                                 m.is_recyclable(), m.is_hazard()) for m in product.get_materials()]
    return row


def register_product(db, data, owner_row, base_url):
    if not to_user(owner_row).can("register_product"):
        raise Forbidden("Your role cannot register products.")
    product = build_product(data)
    # NFR 7: a UUID is never reused, not even one of an archived product (also UNIQUE in the table).
    while db.execute("SELECT 1 FROM products WHERE uuid = ?", (product.get_uuid(),)).fetchone():
        product = build_product(data)  # pragma: no cover  (uuid4 collision, practically impossible)
    row = insert_product(db, product, owner_row)
    get_qr_code(db, row, base_url, commit=False)
    append_event(db, row, owner_row, "registered", "Passport created")
    db.commit()
    return get_product(db, row.uuid)


def update_product(db, row, data, user_row):
    user = to_user(user_row)
    is_owner = row.owner_id == user_row.id
    if not (user.can("edit_any_product") or (is_owner and user.can("edit_own_product"))):
        raise Forbidden("You may only edit your own products.")
    if row.archived:
        raise Conflict("Archived products cannot be edited.")

    merged = {
        "name": row.name, "category": row.category, "lifespan_years": row.lifespan_years,
        "model": row.model, "spare_parts_percent": row.spare_parts_percent,
        "materials": [{"material": m.material, "percent": m.percent, "recycled": m.recycled_share,
                       "recyclable": m.recyclable, "hazard": m.hazard} for m in row.materials],
    }
    merged.update({k: v for k, v in data.items() if k in merged})
    product = build_product(merged, uuid=row.uuid)

    db.execute("UPDATE products SET name = ?, model = ?, category = ?, lifespan_years = ?, "
               "spare_parts_percent = ?, updated_at = ? WHERE id = ?",
               (product.get_name(), product.get_model(), product.get_category(), product.get_lifespan_years(),
                product.get_spare_parts_percent(), _now_iso(), row.id))
    if "materials" in data:
        # old rows are kept for the record, never deleted
        db.execute("UPDATE material_components SET active = 0 WHERE product_id = ?", (row.id,))
        _insert_materials(db, row.id, product)
    append_event(db, row, user_row, "updated", "Changed: " + ", ".join(sorted(data)))
    db.commit()
    return get_product(db, row.uuid)


def archive_product(db, row, user_row):
    if not to_user(user_row).can("archive_product"):
        raise Forbidden("Only an admin can archive products.")
    if not row.archived:
        db.execute("UPDATE products SET archived = 1, updated_at = ? WHERE id = ?", (_now_iso(), row.id))
        append_event(db, row, user_row, "archived", "Product archived")
        db.commit()
    return get_product(db, row.uuid)


def get_product(db, uuid):
    r = db.execute("SELECT * FROM products WHERE uuid = ?", (str(uuid).strip().lower(),)).fetchone()
    if r is None:
        raise NotFound("No product with this UUID.")
    row = ProductRow.from_db(r)
    row.materials = [MaterialRow.from_db(m) for m in db.execute(
        "SELECT * FROM material_components WHERE product_id = ? AND active = 1 ORDER BY id", (row.id,))]
    row.history = [HistoryEventRow.from_db(e, row.uuid) for e in db.execute(
        "SELECT * FROM history_events WHERE product_id = ? ORDER BY id", (row.id,))]
    return row


def search_products(db, q="", category="", page=1, page_size=20, include_archived=False):
    page = max(int(page or 1), 1)
    page_size = min(max(int(page_size or 20), 1), MAX_PAGE_SIZE)
    where, params = [], []
    q = (q or "").strip().lower()
    if q:
        where.append("(uuid LIKE ? ESCAPE '\\' OR lower(name) LIKE ? ESCAPE '\\' "
                     "OR lower(category) LIKE ? ESCAPE '\\')")
        safe = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        params += [f"{safe}%", f"%{safe}%", f"%{safe}%"]
    if category:
        where.append("lower(category) = ?")
        params.append(category.strip().lower())
    if not include_archived:
        where.append("archived = 0")
    clause = (" WHERE " + " AND ".join(where)) if where else ""
    total = db.execute(f"SELECT COUNT(*) FROM products{clause}", params).fetchone()[0]
    rows = [ProductRow.from_db(r) for r in db.execute(
        f"SELECT * FROM products{clause} ORDER BY id DESC LIMIT ? OFFSET ?",
        params + [page_size, (page - 1) * page_size])]
    return rows, total


def list_categories(db):
    stored = {r[0] for r in db.execute("SELECT DISTINCT category FROM products")}
    known = set(_score_calculator.weights.category_lifespans) - {"Other"}
    return sorted(stored | known)


# ---------------------------------------------------------------- QR code
def get_qr_code(db, row, base_url, commit=True):
    passport_url = f"{base_url.rstrip('/')}/passport/{row.uuid}"
    r = db.execute("SELECT target_url, png_bytes FROM qr_codes WHERE product_id = ?", (row.id,)).fetchone()
    if r is not None and r["target_url"] == passport_url:
        return QRCodeRow(r["target_url"], r["png_bytes"])
    qr = Passport(to_product(row), base_url).get_qr_code()
    db.execute("INSERT INTO qr_codes (product_id, target_url, png_bytes, created_at) VALUES (?, ?, ?, ?) "
               "ON CONFLICT(product_id) DO UPDATE SET target_url = excluded.target_url, "
               "png_bytes = excluded.png_bytes",
               (row.id, qr.get_target_url(), qr.get_png_bytes(), _now_iso()))
    if commit:
        db.commit()
    return QRCodeRow(qr.get_target_url(), qr.get_png_bytes())


# ---------------------------------------------------------------- history (Subsystem 2 rules)
def append_event(db, row, actor_row, event_type, details):
    previous = row.history[-1].event_hash if row.history else GENESIS_HASH
    event = HistoryEventRow(row.uuid, event_type, _now_iso(), actor_row.email, actor_row.role,
                            details or "", previous)
    event.event_hash = _hasher.calculate_hash(event)
    cur = db.execute(
        "INSERT INTO history_events (product_id, event_type, timestamp, actor_email, actor_role, details, "
        "previous_hash, event_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (row.id, event.event_type, event.timestamp, event.actor_email, event.actor_role, event.details,
         event.previous_hash, event.event_hash))
    event.id = cur.lastrowid
    row.history.append(event)
    return event


def add_lifecycle_event(db, row, user_row, event_type, details=""):
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Event type must be one of {EVENT_TYPES}.")
    if user_row.role not in EVENT_PERMISSIONS[event_type]:
        raise Forbidden(f"A {user_row.role} cannot add a '{event_type}' event.")
    if row.archived:
        raise Conflict("Archived products cannot get new events.")
    if not isinstance(details, str) or len(details) > 1000:
        raise ValueError("Details must be text of at most 1000 characters.")
    event = append_event(db, row, user_row, event_type, details.strip())
    db.commit()
    return event


def verify_history(row):
    """{'valid': True/False, 'first_broken_event': n}, using Subsystem 2's ChainVerifier."""
    return ChainVerifier(GENESIS_HASH).verify_chain(row.history)


# ---------------------------------------------------------------- score (Subsystem 3)
def circularity_score(row):
    product = {
        "product_id": row.uuid,
        "category": row.category,
        "expected_lifetime_years": row.lifespan_years,
        "spare_parts_percent": row.spare_parts_percent,
        "repair_count": sum(1 for e in row.history if e.event_type == "repaired"),
    }
    materials = [{"material": m.material, "percent": m.percent, "recycled": m.recycled_share,
                  "recyclable": m.recyclable, "hazard": m.hazard} for m in row.materials]
    return _score_calculator.calculate(product, materials).to_dict()


# ---------------------------------------------------------------- passport
def build_passport(row, base_url):
    passport = Passport(to_product(row), base_url)
    passport.set_score(circularity_score(row))
    for event in row.history:
        passport.add_history_event(event.to_dict(public=True))
    return passport


def passport_dict(row, base_url):
    data = build_passport(row, base_url).to_dict()
    data["archived"] = row.archived
    data["history_check"] = verify_history(row)
    data["created_at"] = row.created_at
    return data
