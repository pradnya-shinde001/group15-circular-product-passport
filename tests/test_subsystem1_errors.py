"""Tests for Subsystem 1's error-handling classes.

Run from the project folder:  python -m pytest tests/test_subsystem1_errors.py -v"""
import uuid as uuid_module

import pytest

from subsystem1_passport.auth_service import AuthService
from subsystem1_passport.errors import AccountError, PassportError, ProductNotFoundError, RegistrationError
from subsystem1_passport.passport_service import PassportService


def new_email():
    return f"user-{uuid_module.uuid4().hex[:8]}@example.com"


def manufacturer_id(service):
    return next(user["id"] for user in service.users() if user["role"] == "manufacturer")


def register(service, percent):
    """Try to register a product with one material of the given percent."""
    materials = [{"material": "Glass", "percent": percent, "recycled": False, "recyclable": True, "hazard": False}]
    return service.register_product("Test Phone", "Smartphone", 4, "TP-1", manufacturer_id(service), 50, "Good",
                                    materials)


# ---------- The classes ----------

def test_every_error_is_a_passport_error():
    for error_class in (AccountError, RegistrationError, ProductNotFoundError):
        assert issubclass(error_class, PassportError)


def test_errors_still_work_with_the_existing_except_blocks():
    assert issubclass(AccountError, ValueError)
    assert issubclass(RegistrationError, ValueError)
    assert issubclass(ProductNotFoundError, LookupError)


def test_default_status_codes():
    assert AccountError("Bad").status_code == 400
    assert ProductNotFoundError("Missing").status_code == 404


def test_status_code_can_be_changed():
    assert AccountError("Wrong password", status_code=401).status_code == 401


def test_to_dict():
    assert ProductNotFoundError("Missing").to_dict() == {
        "error": "ProductNotFoundError", "message": "Missing", "status": 404}


# ---------- The services raise them ----------

def test_unknown_product_raises_product_not_found():
    with pytest.raises(ProductNotFoundError):
        PassportService().get_product("does-not-exist")


def test_bad_materials_raise_registration_error_with_the_problem():
    with pytest.raises(RegistrationError) as caught:
        register(PassportService(), 50)
    assert any("100" in problem for problem in caught.value.message)


def test_valid_product_raises_no_error():
    assert register(PassportService(), 100)


def test_sign_up_as_admin_raises_account_error():
    with pytest.raises(AccountError):
        AuthService().sign_up(new_email(), "good-password", "admin")


def test_used_email_raises_account_error():
    with pytest.raises(AccountError, match="already exists"):
        AuthService().sign_up("admin@example.com", "good-password", "consumer")


def test_invalid_email_keeps_the_original_error():
    with pytest.raises(AccountError) as caught:
        AuthService().sign_up("not-an-email", "good-password", "consumer")
    assert isinstance(caught.value.__cause__, ValueError)


def test_wrong_password_raises_account_error_with_401():
    with pytest.raises(AccountError) as caught:
        AuthService().login("admin@example.com", "wrong-password")
    assert caught.value.status_code == 401


# ---------- The web app shows them ----------

def test_unknown_product_in_the_api_returns_404_json(browser):
    response = browser.get("/api/passports/does-not-exist")
    assert response.status_code == 404
    assert "No product" in response.json()["detail"]
