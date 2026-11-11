"""Shows the Subsystem 4 classes.

Run:  python -m subsystem4_ai_engine.demo                   (uses a plain test picture)
      python -m subsystem4_ai_engine.demo my_laptop.jpg     (uses your own photo; it is copied, never deleted)"""
import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image

from .ai_prediction import AIPrediction
from .errors import InvalidPhotoError, InvalidRatingError
from .image_classifier import ImageClassifier
from .llm_adapter import LLMAdapter
from .photo_check import PhotoCheck
from .recommender import Recommender
from .rule_based_advisor import RuleBasedAdvisor

PRODUCT = {"name": "ThinkPad Laptop", "condition": "Good", "repairability_score": 60, "reusability_score": 72}


def make_demo_photos(folder):
    """Make the photos the demo needs. Your own photo is copied, so the demo never deletes the original."""
    if len(sys.argv) > 1:
        photo = folder / Path(sys.argv[1]).name
        shutil.copy(sys.argv[1], photo)
    else:
        photo = folder / "test_picture.png"
        Image.new("RGB", (224, 224), "grey").save(photo)

    gif = folder / "wrong_format.gif"
    Image.new("RGB", (10, 10), "red").save(gif, "GIF")
    return photo, gif


def main():
    folder = Path(tempfile.mkdtemp(prefix="ai-demo-"))
    photo, gif = make_demo_photos(folder)

    print("1. PhotoCheck  (FR 1, NFR 7)")
    check = PhotoCheck()
    print("   Allowed formats:", check.get_allowed_formats(), " Max size:", check.get_max_megabytes(), "MB")
    check.check(photo)
    print(f"   {photo.name}: accepted")
    try:
        check.check(gif)
    except InvalidPhotoError as error:
        print(f"   {gif.name}: rejected -> {error}")

    print("2. ImageClassifier  (FR 2, 3, 4, NFR 4)")
    classifier = ImageClassifier()
    print("   Model:", classifier.get_model_name())
    print("   Loading CLIP, the first time takes a few seconds ...")
    result = classifier.classify(photo)
    print("   Top 3 categories:")
    for guess in result["categories"]:
        print(f"      {guess['label']:<17} {guess['confidence']:.0%}   uncertain: {guess['uncertain']}")
    print("   Top 3 materials:")
    for guess in result["materials"]:
        print(f"      {guess['label']:<17} {guess['confidence']:.0%}   uncertain: {guess['uncertain']}")

    print("3. Delete the photo after identification  (NFR 6)")
    check.delete(photo)
    print(f"   {photo.name} still on disk: {photo.exists()}")

    print("4. Recommender with a reason  (FR 7, 8, 10, NFR 9)")
    adapter = LLMAdapter()
    print("   API key found:", adapter.has_api_key(), " (without a key, the rules answer)")
    recommender = Recommender(adapter)
    recommender.set_advisor(RuleBasedAdvisor())
    prediction = recommender.recommend(PRODUCT)
    print("   Product:", PRODUCT["name"])
    print("   Recommended action:", prediction.get_action())
    print("   Reason:", prediction.get_reason())
    print("   Answered by:", prediction.get_source(), " Model:", prediction.get_model())

    print("5. Rating  (FR 9)")
    prediction.rate(4)
    print("   Rating saved:", prediction.get_rating())
    try:
        prediction.rate(7)
    except InvalidRatingError as error:
        print("   Rating 7 rejected ->", error)

    print("6. AIPrediction getters and setters")
    example = AIPrediction("Repair", "Sample reason.", "demo")
    example.set_action("Reuse")
    print("   Updated action:", example.get_action(), " Created at:", example.get_created_at())

    shutil.rmtree(folder, ignore_errors=True)


if __name__ == "__main__":
    main()
