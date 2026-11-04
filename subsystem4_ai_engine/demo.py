"""Shows the five Subsystem 4 classes.  Run:  python -m subsystem4_ai_engine.demo

It needs no CLIP download. Without KICONNECT_API_KEY, the recommendation comes from the rules.
To identify a real photo with CLIP:  python -m subsystem4_ai_engine.demo path/to/photo.jpg
"""
import os
import sys
import tempfile
import time
from io import BytesIO
from pathlib import Path

from PIL import Image

from .ai_prediction import AIPrediction
from .image_classifier import CATEGORIES, MATERIALS, ImageClassifier, PhotoError, load_photo
from .llm_adapter import LLMAdapter, LLMError
from .recommender import ACTIONS, Recommender
from .rule_based_advisor import RuleBasedAdvisor

# Static sample data. The database layer belongs to Assignment 3.
PRODUCT = {"product_id": "DEMO-001", "product_name": "ThinkPad Laptop", "category": "Laptop", "manufacturer": "Lenovo",
           "manufacturing_year": 2022, "expected_lifetime_years": 9, "current_condition": "Excellent", "repair_count": 3,
           "repairability_score": 60, "reusability_score": 72, "recyclability_score": 100,
           "recycled_material_percent": 8, "battery_recyclable": False}
CIRCULARITY_SCORE = 69.7


def heading(text):
    print(f"\n{text}")


def class_check():
    print("AI ENGINE - OOP CLASS CHECK")
    print("=" * 55)

    classifier = ImageClassifier()
    print(f"1. ImageClassifier: {classifier.model_name}")
    print(f"   Getter top_k: {classifier.top_k}")
    classifier.top_k = 2
    print(f"   Updated top_k: {classifier.top_k}")
    try:
        classifier.top_k = 0
    except ValueError as e:
        print(f"   Setter refuses top_k = 0: {e}")
    print(f"   CLIP loaded: {classifier.is_loaded} (initialize() loads it on first use)")
    buffer = BytesIO()
    Image.new("RGB", (64, 48), "white").save(buffer, "PNG")
    image, fmt = load_photo(buffer.getvalue())
    print(f"   Photo accepted: {fmt}, {image.size[0]} x {image.size[1]}")
    try:
        load_photo(b"this is not a photo")
    except PhotoError as e:
        print(f"   Other files refused: {e}")

    prediction = AIPrediction("recommendation", {"action": "Repair"}, "demo-model", "1", "DEMO-001")
    print(f"2. AIPrediction: {prediction.kind} {prediction.result}")
    print(f"   Getter created_at, set by initialize(): {prediction.created_at}")
    prediction.rating = 4
    print(f"   Updated rating: {prediction.rating}")
    try:
        prediction.rating = 9
    except ValueError as e:
        print(f"   Setter refuses rating = 9: {e}")

    adapter = LLMAdapter("KI:connect.NRW (college)")
    print(f"3. LLMAdapter: {adapter.provider}")
    print(f"   Getter base_url, set by initialize(): {adapter.base_url}")
    print(f"   Getter model: {adapter.model}")
    adapter.max_tokens = 300
    print(f"   Updated max_tokens: {adapter.max_tokens}")
    print(f"   API key set: {adapter.has_api_key} (read from the environment, and never stored in the code)")
    try:
        LLMAdapter("Offline (no API key)").complete("Hello")
    except LLMError as e:
        print(f"   Without an LLM, it reports: {e}")

    advisor = RuleBasedAdvisor()
    print(f"4. RuleBasedAdvisor: {advisor.MODEL_NAME}")
    print(f"   Getter current_year, set by initialize(): {advisor.current_year}")
    print(f"   Getter repair_repairability: {advisor.repair_repairability}")
    advisor.repair_repairability = 70
    print(f"   Updated repair_repairability: {advisor.repair_repairability}")

    recommender = Recommender(advisor=advisor)
    print(f"5. Recommender: LLM adapter {recommender.adapter}, advisor {type(recommender.advisor).__name__}")
    print(f"   Getter timeout, in seconds (connect, read): {recommender.timeout}")
    recommender.timeout = (2, 5)
    print(f"   Updated timeout: {recommender.timeout}")
    try:
        recommender.timeout = (5, 5)
    except ValueError as e:
        print(f"   Setter refuses (5, 5): {e}")


def sample_recommendation():
    heading("INTEGRATED SAMPLE RECOMMENDATION")
    print(f"Product ID: {PRODUCT['product_id']}")
    print(f"Product: {PRODUCT['product_name']} ({PRODUCT['category']}, {PRODUCT['manufacturer']})")
    print(f"Condition: {PRODUCT['current_condition']}")
    print(f"Repairability: {PRODUCT['repairability_score']}")
    print(f"Reusability: {PRODUCT['reusability_score']}")
    print(f"Made in {PRODUCT['manufacturing_year']}, expected life {PRODUCT['expected_lifetime_years']} years")

    adapter = LLMAdapter("KI:connect.NRW (college)")
    start = time.perf_counter()
    prediction = Recommender(adapter if adapter.has_api_key else None).recommend(PRODUCT, CIRCULARITY_SCORE)
    milliseconds = (time.perf_counter() - start) * 1000
    result = prediction.result
    print(f"Action: {result['action']}")
    print(f"Reason: {result['reason']}")
    print(f"Answered by: {result['source']} ({prediction.model_name})")
    if result["source"] == "rules":
        print(f"Why the rules answered: {result['fallback_reason']}")
    print(f"Calculation time: {milliseconds:.1f} ms")

    prediction.rating = 5
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "predictions.jsonl")
        prediction.save(path)
        saved = AIPrediction.latest("recommendation", PRODUCT["product_id"], path)
    print(f"Saved to a file and read back: rating {saved.rating}, created {saved.created_at}")


def how_it_decides():
    advisor = RuleBasedAdvisor()
    heading("HOW IT DECIDES")
    print(f"Possible actions: {', '.join(ACTIONS)}")
    print("Order: the LLM answers first. If there is no LLM, or its answer is unusable, the rules answer.")
    print("Rules:")
    print(f"  Excellent or Good, reusability >= {advisor.resale_reusability}, "
          f"at least {advisor.min_resale_years} years of life left: Resale")
    print(f"  Otherwise Excellent or Good, reusability >= {advisor.reuse_reusability}: Reuse")
    print(f"  Fair or Poor, repairability >= {advisor.repair_repairability}, some life left: Repair")
    print("  Anything else: Recycling")
    print(f"Photo identification: CLIP compares a photo with {len(CATEGORIES)} categories "
          f"and {len(MATERIALS)} materials, and gives the top 3 of each.")


def identify_photo(path):
    heading(f"REAL PHOTO IDENTIFICATION: {path}")
    prediction = ImageClassifier().classify(Path(path).read_bytes())
    for name in ("category", "material"):
        guesses = ", ".join(f"{g['label']} {g['confidence']:.0%}" for g in prediction.result[name])
        print(f"{name.capitalize()}: {guesses}")
    print(f"Model: {prediction.model_name}")


def main():
    class_check()
    sample_recommendation()
    how_it_decides()
    if len(sys.argv) > 1:
        identify_photo(sys.argv[1])


if __name__ == "__main__":
    main()
