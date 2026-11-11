"""AccuracyCheck: measures how often ImageClassifier is right (NFR 1 and NFR 2).

The photos must be in one folder per category; the folder name is the right answer:
    labelled/
        Laptop/      01.jpg  02.jpg ...
        Camera/      01.jpg  ...

Run:  python -m subsystem4_ai_engine.accuracy_check ~/Downloads/ai_test_photos/labelled"""
import sys
import time
from pathlib import Path

from .image_classifier import ImageClassifier


class AccuracyCheck:
    def __init__(self, classifier=None, goal_percent=80, max_seconds=3):
        self._classifier = classifier
        self._goal_percent = goal_percent    # NFR 1: top-3 accuracy of at least 80 %
        self._max_seconds = max_seconds      # NFR 2: under 3 seconds per photo
        self.initialize()

    def initialize(self):
        """Use the real CLIP classifier if no other one was given."""
        if self._classifier is None:
            self._classifier = ImageClassifier()

    def get_classifier(self):
        return self._classifier

    def set_classifier(self, classifier):
        self._classifier = classifier

    def get_goal_percent(self):
        return self._goal_percent

    def get_max_seconds(self):
        return self._max_seconds

    def check_photo(self, photo, right_answer):
        """Classify one photo. Return (in top 1?, in top 3?, seconds it took)."""
        start = time.time()
        result = self._classifier.classify(photo)
        seconds = time.time() - start

        labels = [guess["label"] for guess in result["categories"]]
        return labels[0] == right_answer, right_answer in labels, seconds

    def run(self, folder):
        """Check every photo in the folder. Return a dict with the totals and one line per category."""
        total = top1 = top3 = 0
        times = []
        per_category = {}

        for category_folder in sorted(Path(folder).iterdir()):
            if not category_folder.is_dir():
                continue
            right_answer = category_folder.name
            photos = sorted(p for p in category_folder.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
            correct = 0
            for photo in photos:
                in_top1, in_top3, seconds = self.check_photo(photo, right_answer)
                total += 1
                top1 += in_top1
                top3 += in_top3
                correct += in_top3
                times.append(seconds)
            per_category[right_answer] = (correct, len(photos))

        top3_percent = 100 * top3 / total if total else 0
        return {"photos": total,
                "top1_percent": 100 * top1 / total if total else 0,
                "top3_percent": top3_percent,
                "first_photo_seconds": times[0] if times else 0,   # includes loading CLIP
                "slowest_seconds": max(times[1:], default=0),      # the photos after loading
                "per_category": per_category,
                "passed": top3_percent >= self._goal_percent}


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else Path.home() / "Downloads" / "ai_test_photos" / "labelled"
    check = AccuracyCheck()
    print(f"Checking the photos in {folder} ... (the first photo also loads CLIP)\n")
    result = check.run(folder)

    print(f"{'Category':<18} Right answer in top 3")
    for category, (correct, count) in result["per_category"].items():
        print(f"{category:<18} {correct} of {count}")

    print(f"\nPhotos checked:   {result['photos']}")
    print(f"Top-1 accuracy:   {result['top1_percent']:.0f} %")
    print(f"Top-3 accuracy:   {result['top3_percent']:.0f} %   (goal: at least {check.get_goal_percent()} %)")
    print(f"First photo:      {result['first_photo_seconds']:.1f} s  (includes loading CLIP)")
    print(f"Slowest after:    {result['slowest_seconds']:.2f} s  (goal: under {check.get_max_seconds()} s)")
    print("\nNFR 1:", "PASSED" if result["passed"] else "NOT PASSED")


if __name__ == "__main__":
    main()
