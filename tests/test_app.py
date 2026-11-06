"""Checks that the whole app runs: pages, accounts, products, events, scores and advice.

Run from the project folder:  python -m pytest tests -v"""
import uuid as uuid_module

import pytest

DEMO_PASSWORD = "demo-password"
GOOD_PASSWORD = "good-password"


# ---------- Helpers ----------

def new_email():
    """A different email for every test, so tests never clash."""
    return f"user-{uuid_module.uuid4().hex[:8]}@example.com"


def sign_up(browser, role="consumer", email=None, password=GOOD_PASSWORD, next_page="/"):
    return browser.post("/signup", data={"email": email or new_email(), "password": password,
                                         "role": role, "next": next_page})


def log_in(browser, role):
    """Log in as one of the demo accounts."""
    response = browser.post("/login", data={"email": f"{role}@example.com", "password": DEMO_PASSWORD})
    assert response.status_code == 303


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


def register_product(browser):
    """Register a product as the logged-in user and return its UUID."""
    response = browser.post("/register", data=product_form())
    assert response.status_code == 303
    return response.headers["location"].split("/passport/")[1].split("?")[0]


@pytest.fixture
def product_uuid(browser):
    """A new product, registered by the demo manufacturer. The browser is logged out afterwards."""
    log_in(browser, "manufacturer")
    uuid = register_product(browser)
    browser.post("/logout")
    return uuid


# ---------- Pages open ----------

@pytest.mark.parametrize("path", ["/", "/login", "/signup", "/docs", "/api/products"])
def test_page_opens(browser, path):
    assert browser.get(path).status_code == 200


def test_unknown_passport_shows_not_found(browser):
    assert browser.get("/passport/does-not-exist").status_code == 404


# ---------- Menu ----------

def test_menu_when_logged_out(browser):
    page = browser.get("/").text
    assert "Sign up" in page
    assert "Log in" in page
    assert "Register product" not in page


def test_menu_for_consumer_hides_register_product(browser):
    sign_up(browser, "consumer")
    page = browser.get("/").text
    assert "Log out" in page
    assert "Register product" not in page


def test_menu_for_manufacturer_shows_register_product(browser):
    sign_up(browser, "manufacturer")
    assert "Register product" in browser.get("/").text


# ---------- Sign up ----------

def test_sign_up_logs_the_user_in(browser):
    email = new_email()
    response = sign_up(browser, email=email)
    assert response.status_code == 303
    assert email in browser.get("/").text


def test_sign_up_page_never_offers_admin(browser):
    page = browser.get("/signup").text
    for role in ("consumer", "manufacturer", "recycler"):
        assert f'value="{role}"' in page
    assert 'value="admin"' not in page


def test_nobody_can_sign_up_as_admin(browser):
    response = sign_up(browser, "admin")
    assert response.status_code == 400
    assert "Log out" not in browser.get("/").text


def test_email_can_only_be_used_once(browser):
    response = sign_up(browser, email="admin@example.com")
    assert response.status_code == 400
    assert "already exists" in response.text


def test_email_is_checked_without_caring_about_capitals(browser):
    response = sign_up(browser, email="ADMIN@example.com")
    assert response.status_code == 400


def test_short_password_is_rejected(browser):
    response = sign_up(browser, password="short")
    assert response.status_code == 400
    assert "at least 8 characters." in response.text


def test_invalid_email_is_rejected(browser):
    response = sign_up(browser, email="not-an-email")
    assert response.status_code == 400
    assert "Invalid email" in response.text


def test_sign_up_never_redirects_to_another_website(browser):
    response = sign_up(browser, next_page="//evil.example.com")
    assert response.headers["location"] == "/"


def test_logged_in_user_is_sent_away_from_sign_up(browser):
    sign_up(browser)
    assert browser.get("/signup").status_code == 303


# ---------- Log in and log out ----------

def test_new_user_can_log_out_and_back_in(browser):
    email = new_email()
    sign_up(browser, email=email)
    assert browser.post("/logout").status_code == 303
    assert email not in browser.get("/").text

    response = browser.post("/login", data={"email": email, "password": GOOD_PASSWORD})
    assert response.status_code == 303
    assert email in browser.get("/").text


@pytest.mark.parametrize("role", ["admin", "manufacturer", "recycler", "consumer"])
def test_demo_accounts_can_log_in(browser, role):
    log_in(browser, role)
    assert f"{role}@example.com" in browser.get("/").text


def test_wrong_password_is_rejected(browser):
    response = browser.post("/login", data={"email": "admin@example.com", "password": "wrong-password"})
    assert response.status_code == 401
    assert "Wrong email or password" in response.text


# ---------- Register a product ----------

def test_register_page_needs_a_login(browser):
    response = browser.get("/register")
    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=/register"


@pytest.mark.parametrize("role", ["consumer", "recycler"])
def test_only_manufacturers_and_admins_can_register_products(browser, role):
    sign_up(browser, role)
    assert browser.get("/register").status_code == 403
    assert browser.post("/register", data=product_form()).status_code == 403


@pytest.mark.parametrize("role", ["admin", "manufacturer"])
def test_register_product_creates_a_passport(browser, role):
    log_in(browser, role)
    uuid = register_product(browser)
    page = browser.get(f"/passport/{uuid}")
    assert page.status_code == 200
    assert "Test Laptop" in page.text
    assert "Aluminium" in page.text


def test_materials_must_add_up_to_100(browser):
    log_in(browser, "manufacturer")
    response = browser.post("/register", data=product_form(percent_0="50"))
    assert response.status_code == 400
    assert "100" in response.text


def test_lifespan_must_be_a_number(browser):
    log_in(browser, "manufacturer")
    response = browser.post("/register", data=product_form(lifespan_years="soon"))
    assert response.status_code == 400
    assert "must be a number" in response.text


# ---------- Passport: QR code, score, API ----------

def test_qr_code_is_a_png_image(browser, product_uuid):
    response = browser.get(f"/passport/{product_uuid}/qr.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG")


def test_new_product_gets_a_score(browser, product_uuid):
    response = browser.get(f"/api/passports/{product_uuid}/scores")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_passport_api_returns_the_materials(browser, product_uuid):
    passport = browser.get(f"/api/passports/{product_uuid}").json()
    assert passport["name"] == "Test Laptop"
    assert len(passport["materials"]) == 3


def test_search_finds_a_registered_product(browser, product_uuid):
    results = browser.get("/api/products", params={"q": product_uuid}).json()
    assert len(results) == 1


# ---------- Lifecycle events ----------

def test_adding_an_event_needs_a_login(browser, product_uuid):
    response = browser.post(f"/passport/{product_uuid}/events", data={"event_type": "used"})
    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_consumer_can_record_used(browser, product_uuid):
    log_in(browser, "manufacturer")
    for event_type in ("manufactured", "sold"):
        response = browser.post(f"/passport/{product_uuid}/events", data={"event_type": event_type})
        assert response.status_code == 303
    browser.post("/logout")

    sign_up(browser, "consumer")
    response = browser.post(f"/passport/{product_uuid}/events", data={"event_type": "used", "note": "Daily"})
    assert response.status_code == 303
    assert "Daily" in browser.get(f"/passport/{product_uuid}").text


def test_new_product_cannot_be_used_before_it_is_sold(browser, product_uuid):
    sign_up(browser, "consumer")
    response = browser.post(f"/passport/{product_uuid}/events", data={"event_type": "used"})
    assert response.status_code == 400

def test_recycler_cannot_record_manufactured(browser, product_uuid):
    sign_up(browser, "recycler")
    response = browser.post(f"/passport/{product_uuid}/events", data={"event_type": "manufactured"})
    assert response.status_code == 403


def test_event_chain_stays_intact(browser, product_uuid):
    log_in(browser, "manufacturer")
    for event_type in ("manufactured", "sold"):
        browser.post(f"/passport/{product_uuid}/events", data={"event_type": event_type})
    result = browser.get(f"/api/passports/{product_uuid}/verify")
    assert result.status_code == 200
    assert "intact" in browser.get(f"/passport/{product_uuid}").text


# ---------- AI recommendation (uses the rule-based advisor, so no API key is needed) ----------

def test_recommendation_is_saved(browser, product_uuid):
    response = browser.post(f"/passport/{product_uuid}/advice")
    assert response.status_code == 303
    passport = browser.get(f"/api/passports/{product_uuid}").json()
    assert len(passport["recommendations"]) >= 1
