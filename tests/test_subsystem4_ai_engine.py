"""Tests for Subsystem 4: AI engine. Owner: Pradnya Shinde.

Every test has three steps:
  1. prepare: create what the test needs
  2. do:      call the code we want to test
  3. check:   use `assert` to check the result
`browser` is the test browser from tests/conftest.py; it uses a temporary database.
Run all tests with:  python -m pytest"""
import pytest

from subsystem4_ai_engine.errors import InvalidProductError, LLMError, ProductNotFoundError
from subsystem4_ai_engine.recommendation_service import RecommendationService
from subsystem4_ai_engine.recommender import Recommender
from subsystem4_ai_engine.rule_based_advisor import RuleBasedAdvisor


class BrokenLLM:
    """A pretend LLM that always fails, as if there were no internet."""

    def has_api_key(self):
        return True

    def ask(self, question):
        raise LLMError("No connection.")


# Test 1
def test_rules_choose_resale_for_good_product():
    advisor = RuleBasedAdvisor()
    product = {"condition": "Good", "repairability_score": 60, "reusability_score": 72}

    action, reason = advisor.advise(product)

    assert action == "Resale"


# Test 2
def test_missing_condition_raises_invalid_product_error():
    advisor = RuleBasedAdvisor()
    product = {"repairability_score": 60, "reusability_score": 72}  # no "condition"

    with pytest.raises(InvalidProductError):
        advisor.advise(product)


# Test 3
def test_broken_llm_falls_back_to_rules():
    recommender = Recommender(BrokenLLM())
    product = {"condition": "Good", "repairability_score": 60, "reusability_score": 72}

    prediction = recommender.recommend(product)

    assert prediction.get_source() == "rules"
    assert prediction.get_action() == "Resale"


# Test 4
def test_unknown_product_raises_product_not_found(browser):
    service = RecommendationService()

    with pytest.raises(ProductNotFoundError):
        service.recommend("no-such-product", use_llm=False)


# Test 5
def test_advice_button_saves_recommendation(browser):
    product_uuid = browser.get("/api/products").json()[0]["uuid"]
    service = RecommendationService()
    count_before = len(service.history(product_uuid))

    browser.post(f"/passport/{product_uuid}/advice")

    count_after = len(service.history(product_uuid))
    assert count_after == count_before + 1
