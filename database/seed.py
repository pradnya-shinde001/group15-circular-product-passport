"""Fills the shared database with synthetic demo data: 4 users and 100 products,
each with materials, a lifecycle history (2021-2025), scores and a recommendation.
The data goes in through each subsystem's own service, so every rule is checked.

Run:  python -m database.seed                (deletes and recreates database/passport.db)
      python -m database.seed --count 250    (another number of products)"""
import argparse
import random
from datetime import datetime, timedelta, timezone

from .connection import connect, db_path, init_db

DEMO_PASSWORD = "demo-password"  # local demo only
DEFAULT_COUNT = 100
RANDOM_SEED = 42  # the same seed gives the same products every time
START_DATE = datetime(2021, 1, 1, 9, 0, tzinfo=timezone.utc)

USERS = [("admin@example.com", "admin"), ("manufacturer@example.com", "manufacturer"),
         ("recycler@example.com", "recycler"), ("consumer@example.com", "consumer")]

# Product names per category. The categories are the ones in subsystem3_score/score_config.json.
PRODUCT_NAMES = {
    "Laptop": ["ThinkPad Laptop", "Eco Laptop", "ZenBook Laptop"],
    "Smartphone": ["Galaxy Smartphone", "Fair Phone", "Moto Phone"],
    "Tablet": ["Pro Tablet", "Fire Tablet"],
    "Monitor": ["UltraView Monitor", "Office Monitor"],
    "Desktop computer": ["Tower PC", "Mini PC"],
    "Printer": ["LaserJet Printer", "Ink Printer"],
    "Keyboard": ["Mechanical Keyboard", "Wireless Keyboard"],
    "Headphones": ["Studio Headphones", "Wireless Headphones"],
    "Smartwatch": ["Fitness Watch", "Sport Smartwatch"],
    "Camera": ["Mirrorless Camera", "Action Camera"],
}

# Material: (recyclable, hazardous)
MATERIALS = {
    "Aluminium": (True, False),
    "Plastic": (True, False),
    "Glass": (True, False),
    "Copper": (True, False),
    "Steel": (True, False),
    "Rubber": (False, False),
    "Lithium battery": (True, True),
    "Circuit board": (False, True),
}

CONDITIONS = ["Excellent", "Good", "Fair", "Poor"]

# Who records each event type. Each one is allowed by EventLedger.EVENT_PERMISSIONS.
EVENT_ACTOR = {
    "manufactured": "manufacturer",
    "sold": "manufacturer",
    "used": "consumer",
    "repaired": "consumer",
    "refurbished": "recycler",
    "recycled": "recycler",
}

# A note is picked at random for each event.
NOTES = {
    "manufactured": ["Made in Germany", "Made in Poland", "Made in Czechia"],
    "sold": ["Sold online", "Sold in a shop"],
    "used": ["In daily use"],
    "repaired": ["Battery replaced", "Screen replaced", "Keyboard replaced", "Port repaired"],
    "refurbished": ["Cleaned and tested", "Refurbished for resale"],
    "recycled": ["Materials recovered"],
}


def make_materials(rng):
    """Pick 2 to 4 materials. Each one except the last gets 10, 20 or 30 %;
    the last one gets what is left, so the total is always 100 %."""
    names = rng.sample(list(MATERIALS), rng.randint(2, 4))
    materials = []
    left = 100
    for name in names:
        if name == names[-1]:
            percent = left
        else:
            percent = rng.choice([10, 20, 30])
            left = left - percent
        recyclable, hazard = MATERIALS[name]
        materials.append({"material": name, "percent": percent, "recycled": rng.random() < 0.4,
                          "recyclable": recyclable, "hazard": hazard})
    return materials


def make_events(rng, condition):
    """A history that fits the condition: worn products were repaired more often,
    fair ones may be refurbished, and poor ones are recycled at the end."""
    events = ["manufactured", "sold", "used"]
    if condition in ("Fair", "Poor"):
        repairs = rng.randint(0, 3)
    else:
        repairs = rng.randint(0, 1)
    for _ in range(repairs):
        events.append("repaired")
    if condition == "Fair":
        events.append("refurbished")
    if condition == "Poor":
        events.append("recycled")
    return events


def make_product(rng):
    """One random product, in the form PassportService.register_product needs."""
    category = rng.choice(list(PRODUCT_NAMES))
    name = rng.choice(PRODUCT_NAMES[category])
    condition = rng.choice(CONDITIONS)
    return {
        "name": name,
        "category": category,
        "model": f"{name.split()[0]}-{rng.randint(100, 999)}",
        "lifespan_years": rng.randint(3, 10),
        "spare_parts_percent": rng.randrange(0, 101, 10),
        "condition": condition,
        "materials": make_materials(rng),
        "events": make_events(rng, condition),
    }


def seed(count=DEFAULT_COUNT):
    """Add the 4 users and `count` products through the four subsystem services."""
    # Imported here, because the subsystems themselves import this database package.
    from subsystem1_passport.passport_service import PassportService
    from subsystem2_ledger.ledger_service import LedgerService
    from subsystem3_score.score_service import ScoreService
    from subsystem4_ai_engine.recommendation_service import RecommendationService

    # The same connections as in the web app: a new product or event recalculates the score.
    scores = ScoreService()
    passports = PassportService(on_registered=scores.on_registered)
    ledger = LedgerService(on_event=scores.on_event)
    advice = RecommendationService()

    user_ids = {}
    for email, role in USERS:
        user_ids[role] = passports.add_user(email, role, DEMO_PASSWORD)

    rng = random.Random(RANDOM_SEED)
    for _ in range(count):
        product = make_product(rng)
        uuid = passports.register_product(product["name"], product["category"], product["lifespan_years"],
                                          product["model"], user_ids["manufacturer"],
                                          product["spare_parts_percent"], product["condition"],
                                          product["materials"])

        # The first event happens between 2021 and 2023; each next one 30 to 180 days later.
        # At most 7 events, so the last one is always before November 2026, never in the future.
        date = START_DATE + timedelta(days=rng.randint(0, 1000))
        for event_type in product["events"]:
            actor_id = user_ids[EVENT_ACTOR[event_type]]
            note = rng.choice(NOTES[event_type])
            ledger.add_event(uuid, actor_id, event_type, note, date)
            date = date + timedelta(days=rng.randint(30, 180))

        advice.recommend(uuid, use_llm=False)  # the rule-based advisor: quick and offline


def ensure_demo_data(count=DEFAULT_COUNT):
    """Create the tables, and fill them with demo data when the database is still empty."""
    init_db()
    with connect() as conn:
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if user_count == 0:
        seed(count)


def main():
    parser = argparse.ArgumentParser(description="Recreate the demo database.")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT, help="number of products (default 100)")
    count = parser.parse_args().count

    db_path().unlink(missing_ok=True)  # start from an empty database
    ensure_demo_data(count)
    print(f"Created {db_path()} with {len(USERS)} users and {count} products.")


if __name__ == "__main__":
    main()
