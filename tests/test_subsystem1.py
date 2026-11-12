"""Tests for Subsystem 1: Passport, QR code and web UI. Owner: Mosaddeka Mallick.

TestMain holds the 5 main tests. TestFunctionalRequirements and TestNonFunctionalRequirements
check Subsystem 1's FRs and NFRs; each test's docstring names the requirement it checks.

Run the 5 main tests:        python -m pytest tests/test_subsystem1.py::TestMain -v
Run every Subsystem 1 test:  python -m pytest tests/test_subsystem1.py -v"""
import io
import json
import time
import uuid as uuid_module

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import app
from subsystem1_passport.auth_service import MAX_FAILED_LOGINS, AuthService
from subsystem1_passport.errors import AccountError, ProductNotFoundError, RegistrationError
from subsystem1_passport.material_component import MaterialComponent
from subsystem1_passport.passport import Passport
from subsystem1_passport.passport_service import PassportService
from subsystem1_passport.product import Product
from subsystem1_passport.user import User

DEMO_PASSWORD = "demo-password"
GOOD_PASSWORD = "good-password"


# ---------- Helpers ----------

def product_form(**changes):
    """A valid register form: the materials add up to 100 %."""
    form = {
        "name": "Test Laptop", "model": "TL-1", "category": "Laptop", "lifespan_years": "6",
        "spare_parts_percent": "70", "condition": "Good",
        "material_0": "Aluminium", "percent_0": "60", "recycled_0": "on", "recyclable_0": "on",
        "material_1": "Plastic", "percent_1": "30", "recyclable_1": "on",
        "material_2": "Lithium battery", "percent_2": "10", "hazard_2": "on",
    }
    form.update(changes)
    return form


def new_email():
    """A different email for every test, so tests never clash."""
    return f"user-{uuid_module.uuid4().hex[:8]}@example.com"


def new_browser():
    """A second, separate browser, for a second user."""
    return TestClient(app, follow_redirects=False)


def log_in(browser, role):
    """Log in as one of the demo accounts."""
    browser.post("/login", data={"email": f"{role}@example.com", "password": DEMO_PASSWORD})


def sign_up(browser, role="consumer", email=None):
    return browser.post("/signup", data={"email": email or new_email(), "password": GOOD_PASSWORD, "role": role})


def register_product(browser, **changes):
    """Register a product as the logged-in user and return its UUID."""
    response = browser.post("/register", data=product_form(**changes))
    assert response.status_code == 303
    return response.headers["location"].split("/passport/")[1].split("?")[0]


def valid_product():
    """A Product whose materials add up to 100 %."""
    product = Product("Test Laptop", "Laptop", 6, "TL-1")
    product.add_material(MaterialComponent("Aluminium", 60, recycled=True))
    product.add_material(MaterialComponent("Plastic", 40))
    return product


@pytest.fixture
def product_uuid(browser):
    """A new product registered by the demo manufacturer. The browser is logged out afterwards."""
    log_in(browser, "manufacturer")
    uuid = register_product(browser)
    browser.post("/logout")
    return uuid


# ==================================================================================
# The 5 main tests
# ==================================================================================

class TestMain:
    def test_sign_up_logs_the_user_in(self, browser):
        email = new_email()
        response = sign_up(browser, email=email)
        assert response.status_code == 303
        assert email in browser.get("/").text

    def test_wrong_password_raises_account_error_with_401(self):
        with pytest.raises(AccountError) as caught:
            AuthService().login("admin@example.com", "wrong-password")
        assert caught.value.status_code == 401

    def test_manufacturer_registers_a_product_with_a_passport_and_qr_code(self, browser):
        log_in(browser, "manufacturer")
        uuid = register_product(browser)
        assert "Test Laptop" in browser.get(f"/passport/{uuid}").text
        assert browser.get(f"/passport/{uuid}/qr.png").content.startswith(b"\x89PNG")

    def test_materials_not_adding_up_to_100_raise_registration_error(self):
        service = PassportService()
        manufacturer = next(user["id"] for user in service.users() if user["role"] == "manufacturer")
        materials = [{"material": "Glass", "percent": 50, "recycled": False, "recyclable": True, "hazard": False}]
        with pytest.raises(RegistrationError) as caught:
            service.register_product("Test Phone", "Smartphone", 4, "TP-1", manufacturer, 50, "Good", materials)
        assert any("100" in problem for problem in caught.value.message)

    def test_unknown_product_raises_product_not_found_with_404(self):
        with pytest.raises(ProductNotFoundError) as caught:
            PassportService().get_product("does-not-exist")
        assert caught.value.status_code == 404


# ==================================================================================
# Functional requirements
# ==================================================================================

class TestFunctionalRequirements:
    def test_fr1_registered_product_keeps_all_its_details(self, browser, product_uuid):
        """FR 1: register a product with name, model, category, materials and lifespan."""
        passport = browser.get(f"/api/passports/{product_uuid}").json()
        assert (passport["name"], passport["model"], passport["category"]) == ("Test Laptop", "TL-1", "Laptop")
        assert passport["lifespan_years"] == 6
        assert [m["material"] for m in passport["materials"]] == ["Aluminium", "Plastic", "Lithium battery"]

    def test_fr2_every_product_gets_its_own_valid_uuid(self, browser):
        """FR 2: assign a unique UUID to every product."""
        log_in(browser, "manufacturer")
        first, second = register_product(browser), register_product(browser)
        assert first != second
        assert str(uuid_module.UUID(first)) == first  # a real UUID, not just any text

    def test_fr3_qr_code_links_to_the_passport_page(self):
        """FR 3: generate a QR code linking to the passport page."""
        product = valid_product()
        passport = Passport(product, "https://passport.example.org")
        assert passport.get_public_url() == f"https://passport.example.org/passport/{product.get_uuid()}"
        assert passport.get_qr_code().get_target_url() == passport.get_public_url()

    def test_fr4_passport_page_opens_without_a_login(self, browser, product_uuid):
        """FR 4: show the passport page on scan, with no login needed."""
        page = browser.get(f"/passport/{product_uuid}")
        assert page.status_code == 200
        assert "Test Laptop" in page.text
        assert "Log in" in page.text  # the visitor really is logged out

    def test_fr5_materials_must_total_exactly_100(self, browser):
        """FR 5: check that material percentages sum to 100 %."""
        product = Product("Laptop", "Laptop", 5, "L-1")
        product.add_material(MaterialComponent("Aluminium", 60))
        product.add_material(MaterialComponent("Plastic", 39.9))
        assert not product.materials_valid()
        log_in(browser, "manufacturer")
        response = browser.post("/register", data=product_form(percent_0="50"))
        assert response.status_code == 400
        assert "expected 100%" in response.text

    @pytest.mark.parametrize("changes, missing", [
        ({"model": ""}, "Product model is required."),
        ({"material_0": "", "material_1": "", "material_2": ""}, "materials"),
        ({"lifespan_years": "soon"}, "Lifespan must be a number."),
    ])
    def test_fr6_incomplete_registration_names_what_is_missing(self, browser, changes, missing):
        """FR 6: reject incomplete registrations and name the missing fields."""
        log_in(browser, "manufacturer")
        response = browser.post("/register", data=product_form(**changes))
        assert response.status_code == 400
        assert missing in response.text

    @pytest.mark.parametrize("field", ["uuid", "name", "category"])
    def test_fr7_search_by_uuid_name_or_category(self, browser, field):
        """FR 7: search products by UUID, name or category."""
        log_in(browser, "manufacturer")
        uuid = register_product(browser, name=f"Searchable {uuid_module.uuid4().hex[:6]}")
        text = PassportService().get_product(uuid)[field]
        assert uuid in [p["uuid"] for p in browser.get("/api/products", params={"q": text}).json()]

    def test_fr8_there_are_four_roles_and_nobody_signs_up_as_admin(self, browser):
        """FR 8: four roles with role-based permissions."""
        assert set(User.ROLES) == {"admin", "manufacturer", "recycler", "consumer"}
        assert sign_up(browser, "admin").status_code == 400

    @pytest.mark.parametrize("role", ["consumer", "recycler"])
    def test_fr8_only_manufacturers_and_admins_register_or_edit(self, browser, product_uuid, role):
        """FR 8: role-based permissions for registering and editing."""
        sign_up(browser, role)
        assert browser.post("/register", data=product_form()).status_code == 403
        assert browser.post(f"/passport/{product_uuid}/edit", data={"name": "X", "model": "X"}).status_code == 403

    def test_fr9_passport_page_shows_score_and_history(self, browser, product_uuid):
        """FR 9: show the circularity score and history on the page."""
        page = browser.get(f"/passport/{product_uuid}").text
        assert "Circularity score" in page and "/ 100" in page
        assert "Lifecycle history" in page and "Hash chain" in page

    def test_fr10_passport_can_be_exported_as_json(self, browser, product_uuid):
        """FR 10: export a passport as JSON via REST."""
        response = browser.get(f"/api/passports/{product_uuid}")
        assert response.headers["content-type"] == "application/json"
        assert response.json()["uuid"] == product_uuid
        assert json.loads(Passport(valid_product()).export_json())["name"] == "Test Laptop"


# ==================================================================================
# Non-functional requirements
# ==================================================================================

class TestNonFunctionalRequirements:
    def test_nfr1_passport_page_loads_in_under_2_seconds(self, browser, product_uuid):
        """NFR 1: the passport page loads in under 2 s (measured on this computer)."""
        start = time.perf_counter()
        assert browser.get(f"/passport/{product_uuid}").status_code == 200
        assert time.perf_counter() - start < 2

    def test_nfr3_pages_are_set_up_for_phone_screens(self, browser):
        """NFR 3: usable on phones from 360 px width (the page scales to the screen)."""
        assert 'name="viewport" content="width=device-width, initial-scale=1"' in browser.get("/").text

    def test_nfr5_passwords_are_salted_hashes(self):
        """NFR 5: passwords are hashed, never stored as plain text."""
        first = User("a@example.com", "consumer", GOOD_PASSWORD).get_password_hash()
        second = User("b@example.com", "consumer", GOOD_PASSWORD).get_password_hash()
        assert GOOD_PASSWORD not in first
        assert first != second  # a different salt each time

    def test_nfr5_changing_anything_needs_a_login(self, browser, product_uuid):
        """NFR 5: login required to edit."""
        for path in ("/register", f"/passport/{product_uuid}/edit"):
            assert browser.post(path, data=product_form()).headers["location"].startswith("/login")
        assert browser.post(f"/passport/{product_uuid}/events", data={"event_type": "used"}).status_code == 303

    def test_nfr5_too_many_wrong_passwords_lock_the_account(self, browser):
        """NFR 5: accounts are protected against password guessing."""
        email = new_email()
        sign_up(new_browser(), email=email)
        for _ in range(MAX_FAILED_LOGINS):
            browser.post("/login", data={"email": email, "password": "wrong-password"})
        assert browser.post("/login", data={"email": email, "password": GOOD_PASSWORD}).status_code == 429

    def test_nfr6_qr_code_is_a_square_png(self, browser, product_uuid):
        """NFR 6: the QR code is a clean square image that prints well at 2 x 2 cm."""
        image = Image.open(io.BytesIO(browser.get(f"/passport/{product_uuid}/qr.png").content))
        assert image.format == "PNG"
        assert image.width == image.height >= 250

    def test_nfr7_uuid_can_never_change(self, browser, product_uuid):
        """NFR 7: UUIDs are never reused or changed, even when a product is edited."""
        assert not hasattr(valid_product(), "set_uuid")
        log_in(browser, "manufacturer")
        browser.post(f"/passport/{product_uuid}/edit", data={"name": "Renamed", "model": "R-1", "uuid": "hacked"})
        assert PassportService().get_product(product_uuid)["name"] == "Renamed"
        assert browser.get(f"/api/passports/{product_uuid}").json()["uuid"] == product_uuid

    def test_nfr7_nothing_can_be_deleted(self):
        """NFR 7: no hard deletes. The app has no route that deletes anything."""
        methods = {method for route in app.routes for method in getattr(route, "methods", set())}
        assert "DELETE" not in methods

    def test_nfr8_unknown_product_gives_a_json_404(self, browser):
        """NFR 8: JSON responses with standard HTTP codes."""
        response = browser.get("/api/passports/does-not-exist")
        assert response.status_code == 404
        assert response.json() == {"detail": "No product with the UUID does-not-exist."}

    def test_nfr9_api_is_documented_with_openapi(self, browser):
        """NFR 9: the API is documented automatically (OpenAPI)."""
        assert browser.get("/docs").status_code == 200
        paths = browser.get("/openapi.json").json()["paths"]
        assert "/api/products" in paths and "/api/passports/{uuid}" in paths

