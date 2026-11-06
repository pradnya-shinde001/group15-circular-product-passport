"""Subsystem 1's 5 main tests: sign-up, product registration, QR code and error handling.

Run from the project folder:  python -m pytest tests/test_subsystem1.py -v"""
import uuid as uuid_module

import pytest

from subsystem1_passport.auth_service import AuthService
from subsystem1_passport.errors import AccountError, ProductNotFoundError, RegistrationError
from subsystem1_passport.passport_service import PassportService


def product_form():
    """A valid register form: the materials add up to 100 %."""
    return {
        "name": "Test Laptop", "model": "TL-1", "category": "Laptop", "lifespan_years": "6",
        "spare_parts_percent": "70", "condition": "Good",
        "material_0": "Aluminium", "percent_0": "60", "recycled_0": "on", "recyclable_0": "on",
        "material_1": "Plastic", "percent_1": "30", "recyclable_1": "on",
        "material_2": "Lithium battery", "percent_2": "10", "hazard_2": "on",
    }


def test_sign_up_logs_the_user_in(browser):
    email = f"user-{uuid_module.uuid4().hex[:8]}@example.com"
    response = browser.post("/signup", data={"email": email, "password": "good-password", "role": "consumer"})
    assert response.status_code == 303
    assert email in browser.get("/").text


def test_wrong_password_raises_account_error_with_401():
    with pytest.raises(AccountError) as caught:
        AuthService().login("admin@example.com", "wrong-password")
    assert caught.value.status_code == 401


def test_manufacturer_registers_a_product_with_a_passport_and_qr_code(browser):
    browser.post("/login", data={"email": "manufacturer@example.com", "password": "demo-password"})
    response = browser.post("/register", data=product_form())
    assert response.status_code == 303

    uuid = response.headers["location"].split("/passport/")[1].split("?")[0]
    assert "Test Laptop" in browser.get(f"/passport/{uuid}").text
    assert browser.get(f"/passport/{uuid}/qr.png").content.startswith(b"\x89PNG")


def test_materials_not_adding_up_to_100_raise_registration_error():
    service = PassportService()
    manufacturer = next(user["id"] for user in service.users() if user["role"] == "manufacturer")
    materials = [{"material": "Glass", "percent": 50, "recycled": False, "recyclable": True, "hazard": False}]
    with pytest.raises(RegistrationError) as caught:
        service.register_product("Test Phone", "Smartphone", 4, "TP-1", manufacturer, 50, "Good", materials)
    assert any("100" in problem for problem in caught.value.message)


def test_unknown_product_raises_product_not_found_with_404():
    with pytest.raises(ProductNotFoundError) as caught:
        PassportService().get_product("does-not-exist")
    assert caught.value.status_code == 404
