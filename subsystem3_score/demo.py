"""Shows the five Subsystem 3 classes on static sample data.  Run:  python -m subsystem3_score.demo"""
from types import SimpleNamespace

from .circularity_score import CircularityScore
from .grade import GRADES, Grade
from .score_calculator import ScoreCalculator
from .score_weights import FORMULA, ScoreWeights
from .sub_score import LABELS, SubScore

# Static sample data. The database layer belongs to Assignment 3.
PRODUCT = {"product_id": "DEMO-001", "category": "Laptop", "expected_lifetime_years": 9, "spare_parts_percent": 50,
           "repair_count": 1}
MATERIALS = [{"material": "Aluminium", "percent": 60, "recycled": 40, "recyclable": True, "hazard": False},
             {"material": "Plastic", "percent": 30, "recycled": 10, "recyclable": True, "hazard": False},
             {"material": "Lithium battery", "percent": 10, "recycled": 0, "recyclable": True, "hazard": True}]


def class_check():
    print("CIRCULARITY SCORE ENGINE - OOP CLASS CHECK")
    print("=" * 55)

    weights = ScoreWeights()
    print(f"1. ScoreWeights: {weights.weights}, read by initialize()")
    print(f"   Getter lifespan_for('Laptop'): {weights.lifespan_for('Laptop')}")
    try:
        weights.weights = {"recycled_content": 1}
    except ValueError as e:
        print(f"   Setter refuses incomplete weights: {e}")

    grade = Grade("a", 80)
    print(f"2. Grade: {grade.letter}, upper case from initialize(), minimum {grade.min_score}")
    grade.min_score = 81
    print(f"   Updated minimum: {grade.min_score}")
    try:
        grade.letter = "Z"
    except ValueError as e:
        print(f"   Setter refuses 'Z': {e}")

    sub_score = SubScore("hazard", 87.456, 0.1)
    print(f"3. SubScore: {sub_score.label} {sub_score.value}, rounded by initialize(), weight {sub_score.weight}")
    sub_score.value = 90
    print(f"   Updated value: {sub_score.value}, adds {sub_score.points} points")
    try:
        sub_score.value = 120
    except ValueError as e:
        print(f"   Setter refuses 120: {e}")

    score = CircularityScore("DEMO-001", 72.34, [sub_score])
    print(f"4. CircularityScore: {score.product_id} {score.total}, rounded by initialize()")
    print(f"   Grade getter, worked out by initialize(): {score.grade.letter}")
    score.missing = ["Lifespan"]
    print(f"   Updated missing: {score.missing}, incomplete: {score.incomplete}")
    try:
        score.total = 120
    except ValueError as e:
        print(f"   Setter refuses 120: {e}")

    calculator = ScoreCalculator()
    print(f"5. ScoreCalculator: weights loaded by initialize(): {calculator.weights.weights}")
    calculator.weights = ScoreWeights()
    print(f"   Updated weights object: {type(calculator.weights).__name__}")
    try:
        calculator.weights = {"hazard": 1}
    except TypeError as e:
        print(f"   Setter refuses a plain dict: {e}")


def sample_calculation():
    print("\nINTEGRATED SAMPLE CALCULATION")
    calculator = ScoreCalculator()
    calculator.add_product(PRODUCT, MATERIALS)
    calculator.recalculate(PRODUCT["product_id"])
    # The ledger reports a repair, which raises the repairability sub-score.
    calculator.on_event(SimpleNamespace(product_id=PRODUCT["product_id"], event_type="repaired", corrects_event_id=None))

    score = calculator.latest(PRODUCT["product_id"])
    print(f"Product ID: {score.product_id}")
    print(f"Total score: {score.total}")
    print(f"Grade: {score.grade.letter}")
    print(f"Incomplete: {score.incomplete}")
    print(f"Timestamp: {score.computed_at}")
    print("Sub-score breakdown:")
    for sub in score.sub_scores:
        print(f"  {sub.label}: {sub.value} (weight {sub.weight:.2f})")
    print(f"Score history, before and after a repair: {[item.total for item in calculator.history(PRODUCT['product_id'])]}")


def formulas():
    weights = ScoreWeights().weights
    print("\nFORMULAS AND WEIGHTS")
    print("Weighted total = " + " + ".join(f"{weights[name]} x {label}" for name, label in LABELS.items()))
    for name, label in LABELS.items():
        print(f"{label} = {FORMULA[name]}")
    print("Grades: " + ", ".join(f"{grade.letter} >= {grade.min_score}" for grade in GRADES))


def main():
    class_check()
    sample_calculation()
    formulas()


if __name__ == "__main__":
    main()
