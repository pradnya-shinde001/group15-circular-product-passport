"""PassportService: Subsystem 1's work on the shared database.
Registers users and products, and gives the passport data and QR code."""
import os

from .errors import NotAllowedError, ProductEditError, ProductNotFoundError, RegistrationError
from .material_component import MaterialComponent
from .passport import Passport
from .passport_repository import ProductRepository, UserRepository
from .product import Product
from .qr_code import QRCode
from .user import User

CONDITIONS = ["Excellent", "Good", "Fair", "Poor"]
REGISTER_ROLES = ("admin", "manufacturer")
MAX_TEXT_LENGTH = 100  # longest name or model allowed when editing


class PassportService:
    def __init__(self, on_registered=None, base_url=None):
        """on_registered(uuid) is called after each new product, for example to calculate its score."""
        self._on_registered = on_registered
        self._base_url = base_url or os.environ.get("PASSPORT_BASE_URL", "http://localhost:8000")
        self._users = UserRepository()
        self._products = ProductRepository()

    # ---- users ----
    def add_user(self, email, role, password):
        return self._users.add(User(email, role, password))

    def users(self):
        return self._users.all()

    # ---- products ----
    def register_product(self, name, category, lifespan_years, model, owner_id, spare_parts_percent, condition,
                         materials):
        """Validate with the Product, MaterialComponent and Passport classes, then save.
        `materials` is a list of dicts: material, percent, recycled, recyclable, hazard.
        Returns the new UUID. Raises RegistrationError with the list of every problem found."""
        problems = []
        owner = self._users.get(owner_id)
        if owner is None or owner["role"] not in REGISTER_ROLES:
            problems.append("Only a manufacturer or an admin can register a product.")
        if condition not in CONDITIONS:
            problems.append(f"Condition must be one of {', '.join(CONDITIONS)}.")
        if spare_parts_percent is None or not 0 <= spare_parts_percent <= 100:
            problems.append("Spare-part availability must be between 0 and 100 %.")
        try:
            product = Product(name, category, lifespan_years, model)
            saved = []
            for m in materials:
                component = MaterialComponent(m["material"], m["percent"], m["recycled"], m["hazard"])
                product.add_material(component)
                saved.append({**component.to_dict(), "recyclable": m["recyclable"]})
            passport = Passport(product, self._base_url)  # checks the materials sum to 100 %, builds the URL
        except ValueError as e:
            problems.append(str(e))
        if problems:
            raise RegistrationError(problems)
        self._products.add(product, saved, passport.get_public_url(), owner_id, spare_parts_percent, condition)
        if self._on_registered is not None:
            self._on_registered(product.get_uuid())
        return product.get_uuid()

    def can_edit(self, product, user):
        """Only the user who registered the product, or an admin, may edit it."""
        return user is not None and (user["role"] == "admin" or product["owner_id"] == user["id"])

    def update_details(self, uuid, user, name, model):
        """Change a product's name and model, for example to fix a typo.
        Nothing else can change, so the UUID, QR code, materials, score and history stay trustworthy.
        Raises ProductNotFoundError, NotAllowedError, or ProductEditError with every problem found."""
        product = self.get_product(uuid)
        if not self.can_edit(product, user):
            raise NotAllowedError("Only the manufacturer who registered this product, or an admin, can edit it.")
        name = (name or "").strip()
        model = (model or "").strip()
        problems = []
        if not name:
            problems.append("Product name is required.")
        if len(name) > MAX_TEXT_LENGTH:
            problems.append(f"Product name can be at most {MAX_TEXT_LENGTH} characters.")
        if len(model) > MAX_TEXT_LENGTH:
            problems.append(f"Model can be at most {MAX_TEXT_LENGTH} characters.")
        if problems:
            raise ProductEditError(problems)
        self._products.update_details(uuid, name, model)

    def get_product(self, uuid):
        """The product, or ProductNotFoundError when there is none."""
        product = self._products.get(uuid)
        if product is None:
            raise ProductNotFoundError(f"No product with the UUID {uuid}.")
        return product

    def materials(self, uuid):
        return self._products.materials(uuid)

    def search(self, text=""):
        return self._products.search(text)

    def qr_png(self, uuid):
        return QRCode(self.get_product(uuid)["public_url"]).get_png_bytes()
