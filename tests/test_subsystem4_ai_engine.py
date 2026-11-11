"""Tests for Subsystem 4: AI engine. Owner: Pradnya Shinde.

Every test has three steps:
  1. prepare: create what the test needs
  2. do:      call the code we want to test
  3. check:   use `assert` to check the result
`browser` is the test browser from tests/conftest.py; it uses a temporary database.
Run all tests with:  python -m pytest"""
import pytest
from PIL import Image

from subsystem4_ai_engine.ai_prediction import AIPrediction
from subsystem4_ai_engine.errors import (InvalidPhotoError, InvalidProductError, InvalidRatingError, LLMError,
                                         PredictionNotFoundError, ProductNotFoundError)
from subsystem4_ai_engine.image_classifier import ImageClassifier
from subsystem4_ai_engine.photo_check import PhotoCheck
from subsystem4_ai_engine.recommendation_service import RecommendationService
from subsystem4_ai_engine.recommender import Recommender
from subsystem4_ai_engine.rule_based_advisor import RuleBasedAdvisor


class BrokenLLM:
    """A pretend LLM that always fails, as if there were no internet."""

    def has_api_key(self):
        return True

    def ask(self, question):
        raise LLMError("No connection.")


class FakeLLM:
    """A pretend LLM that always gives the same answer, so the tests never call the real, paid one."""

    def __init__(self, answer):
        self.answer = answer

    def has_api_key(self):
        return True

    def get_model(self):
        return "fake-llm-v1"

    def ask(self, question):
        return self.answer


class FakeClassifier:
    """A pretend CLIP, so the tests do not need to download the real model."""

    def classify(self, photo_path):
        return {"categories": [{"label": "Laptop", "confidence": 0.9, "uncertain": False}],
                "materials": [{"label": "Aluminium", "confidence": 0.7, "uncertain": False}],
                "model": "fake-clip"}


def make_photo(folder, name="photo.png", photo_format="PNG"):
    """Create a small red photo for a test and return its path."""
    path = folder / name
    Image.new("RGB", (10, 10), "red").save(path, photo_format)
    return path


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
    log_in_as_manufacturer(browser)   # the button needs a login, because it may call the paid LLM
    product_uuid = browser.get("/api/products").json()[0]["uuid"]
    service = RecommendationService()
    count_before = len(service.history(product_uuid))

    browser.post(f"/passport/{product_uuid}/advice")

    count_after = len(service.history(product_uuid))
    assert count_after == count_before + 1


# ---------- New in the FR-subsystem branch ----------

# Test 6  (FR 4, NFR 4)
def test_top_three_predictions_are_sorted_and_low_ones_are_uncertain():
    classifier = ImageClassifier()

    results = classifier.top_predictions(["Laptop", "Tablet", "Camera", "Printer"], [0.10, 0.60, 0.25, 0.05])

    assert [result["label"] for result in results] == ["Tablet", "Camera", "Laptop"]
    assert results[0]["uncertain"] is False   # 60 % is sure enough
    assert results[1]["uncertain"] is True    # 25 % is under 30 %


# Test 7  (FR 1)
def test_png_and_jpg_photos_are_accepted(tmp_path):
    check = PhotoCheck()
    png = make_photo(tmp_path, "photo.png", "PNG")
    jpg = make_photo(tmp_path, "photo.jpg", "JPEG")

    check.check(png)   # no error means the photo is accepted
    check.check(jpg)


# Test 8  (NFR 7)
def test_wrong_format_is_rejected(tmp_path):
    check = PhotoCheck()
    gif = make_photo(tmp_path, "photo.gif", "GIF")

    with pytest.raises(InvalidPhotoError):
        check.check(gif)


# Test 9  (NFR 7)
def test_text_file_is_rejected(tmp_path):
    check = PhotoCheck()
    fake_photo = tmp_path / "photo.png"
    fake_photo.write_text("I am not a photo")

    with pytest.raises(InvalidPhotoError):
        check.check(fake_photo)


# Test 10  (NFR 7)
def test_photo_over_10_mb_is_rejected(tmp_path):
    check = PhotoCheck()
    big_file = tmp_path / "big.png"
    big_file.write_bytes(b"0" * (11 * 1024 * 1024))   # 11 MB

    with pytest.raises(InvalidPhotoError):
        check.check(big_file)


# Test 11  (FR 2, FR 3, NFR 6)
def test_identify_photo_returns_the_result_and_deletes_the_photo(tmp_path):
    service = RecommendationService()
    service.set_classifier(FakeClassifier())
    photo = make_photo(tmp_path)

    result = service.identify_photo(photo)

    assert result["categories"][0]["label"] == "Laptop"
    assert result["materials"][0]["label"] == "Aluminium"
    assert not photo.exists()


# Test 12  (NFR 6)
def test_identify_photo_keeps_the_photo_when_asked(tmp_path):
    service = RecommendationService()
    service.set_classifier(FakeClassifier())
    photo = make_photo(tmp_path)

    service.identify_photo(photo, keep_photo=True)

    assert photo.exists()


# Test 13  (NFR 6)
def test_rejected_photo_is_deleted_too(tmp_path):
    service = RecommendationService()
    gif = make_photo(tmp_path, "photo.gif", "GIF")

    with pytest.raises(InvalidPhotoError):
        service.identify_photo(gif)

    assert not gif.exists()


# Test 14  (FR 8)
def test_llm_reason_is_kept():
    recommender = Recommender(FakeLLM("Repair: The repairability score of 80 is high."))
    product = {"condition": "Poor", "repairability_score": 80, "reusability_score": 20}

    prediction = recommender.recommend(product)

    assert prediction.get_action() == "Repair"
    assert prediction.get_reason() == "The repairability score of 80 is high."


# Test 15  (FR 8)
def test_llm_answer_without_reason_gets_the_rule_reason():
    recommender = Recommender(FakeLLM("Repair"))
    product = {"condition": "Poor", "repairability_score": 80, "reusability_score": 20}

    prediction = recommender.recommend(product)

    assert prediction.get_source() == "llm"
    assert "repairability is 80" in prediction.get_reason()


# Test 16  (NFR 9)
def test_prediction_saves_the_model_name():
    llm_prediction = Recommender(FakeLLM("Reuse: It still works.")).recommend(
        {"condition": "Good", "repairability_score": 50, "reusability_score": 50})
    rules_prediction = Recommender(BrokenLLM()).recommend(
        {"condition": "Good", "repairability_score": 50, "reusability_score": 50})

    assert llm_prediction.get_model() == "fake-llm-v1"
    assert rules_prediction.get_model() == "rules-v1"


# Test 17  (FR 9)
@pytest.mark.parametrize("bad_rating", [0, 6, 3.5, "4"])
def test_rating_must_be_1_to_5(bad_rating):
    prediction = AIPrediction("Repair", "Some reason.", "rules")

    with pytest.raises(InvalidRatingError):
        prediction.rate(bad_rating)


# Test 18  (FR 9, NFR 9)
def test_rating_is_saved_in_the_database(browser):
    product_uuid = browser.get("/api/products").json()[0]["uuid"]
    service = RecommendationService()
    service.recommend(product_uuid, use_llm=False)
    newest = service.history(product_uuid)[0]

    service.rate(newest["id"], 4)

    saved = service.history(product_uuid)[0]
    assert saved["rating"] == 4
    assert saved["model"] == "rules-v1"


# Test 19  (FR 9)
def test_rating_an_unknown_recommendation_raises_an_error(browser):
    service = RecommendationService()

    with pytest.raises(PredictionNotFoundError):
        service.rate(999999, 4)


# ---------- The web app ----------

def log_in_as_manufacturer(browser):
    browser.post("/login", data={"email": "manufacturer@example.com", "password": "demo-password", "next": "/"})


# Test 20  (FR 1, NFR 7)
def test_app_rejects_a_text_file_as_photo(browser):
    log_in_as_manufacturer(browser)

    response = browser.post("/register/photo", files={"photo": ("notes.txt", b"hello", "text/plain")})

    assert response.status_code == 400
    assert "not a photo" in response.text


# Test 21  (FR 9)
def test_app_saves_a_rating(browser):
    product_uuid = browser.get("/api/products").json()[0]["uuid"]
    browser.post(f"/passport/{product_uuid}/advice")
    prediction_id = browser.get(f"/api/passports/{product_uuid}").json()["recommendations"][0]["id"]

    browser.post(f"/passport/{product_uuid}/advice/{prediction_id}/rate", data={"rating": "5"})

    newest = browser.get(f"/api/passports/{product_uuid}").json()["recommendations"][0]
    assert newest["rating"] == 5


# Test 22  (FR 6)
def test_photo_fills_in_aluminium_and_ticks_recyclable(browser, tmp_path):
    import app
    app.advice.set_classifier(FakeClassifier())   # FakeClassifier says: Laptop, Aluminium
    log_in_as_manufacturer(browser)
    photo = make_photo(tmp_path)

    response = browser.post("/register/photo", files={"photo": ("photo.png", photo.read_bytes(), "image/png")})

    app.advice.set_classifier(ImageClassifier())  # put the real one back for the other tests
    assert response.status_code == 200
    assert 'value="Aluminium"' in response.text
    assert 'name="recyclable_0" checked' in response.text


# Test 23  (NFR 1)
def test_accuracy_check_counts_right_and_wrong_answers(tmp_path):
    from subsystem4_ai_engine.accuracy_check import AccuracyCheck
    (tmp_path / "Laptop").mkdir()
    (tmp_path / "Camera").mkdir()
    make_photo(tmp_path / "Laptop", "01.png")   # FakeClassifier always says Laptop: right
    make_photo(tmp_path / "Camera", "01.png")   # ... and wrong here

    result = AccuracyCheck(FakeClassifier()).run(tmp_path)

    assert result["photos"] == 2
    assert result["top3_percent"] == 50
    assert result["per_category"] == {"Camera": (0, 1), "Laptop": (1, 1)}
    assert result["passed"] is False            # 50 % is under the 80 % goal


# Test 24  (NFR 9)
def test_photo_identification_is_saved_with_the_model_name(browser, tmp_path):
    service = RecommendationService()
    service.set_classifier(FakeClassifier())
    count_before = len(service.identifications())

    service.identify_photo(make_photo(tmp_path))

    saved = service.identifications()
    assert len(saved) == count_before + 1
    assert saved[0]["category"] == "Laptop"
    assert saved[0]["material"] == "Aluminium"
    assert saved[0]["model"] == "fake-clip"
