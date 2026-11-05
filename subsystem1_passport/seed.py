import argparse
import random
import time

from . import repository as repo
from .database import Database

DEMO_PASSWORD = "demo-pass-123"
DEMO_USERS = {
    "admin@demo.local": "admin",
    "maker@demo.local": "manufacturer",
    "recycler@demo.local": "recycler",
    "consumer@demo.local": "consumer",
}

PRODUCT_NAMES = [
    ("ThinkPad Laptop", "Laptop", "Lenovo"),
    ("Galaxy Smartphone", "Smartphone", "Samsung"),
    ("UltraView Monitor", "Monitor", "Dell"),
    ("Pro Tablet", "Tablet", "Samsung"),
    ("Eco Laptop", "Laptop", "HP"),
    ("Office Monitor", "Monitor", "LG"),
]
MATERIALS = [ 
    ("Aluminium", True, False), ("Plastic", True, False), ("Copper", True, False),
    ("Glass", True, False), ("Lithium battery", True, True),
]


def random_materials(rng):
    chosen = rng.sample(MATERIALS, rng.randint(3, len(MATERIALS)))
    cuts = sorted(rng.sample(range(5, 96, 5), len(chosen) - 1))
    shares = [b - a for a, b in zip([0] + cuts, cuts + [100])]
    return [{"material": name, "percent": share, "recycled": rng.choice([0, 10, 25, 40, 70]),
             "recyclable": recyclable, "hazard": hazard}
            for (name, recyclable, hazard), share in zip(chosen, shares)]


def ensure_demo_users(db):
    users = {}
    for email, role in DEMO_USERS.items():
        row = repo.authenticate(db, email, DEMO_PASSWORD)
        users[role] = row or repo.create_user(db, email, DEMO_PASSWORD, role)
    return users


def seed(db, count=100, seed_value=42, batch=500):
    rng = random.Random(seed_value)
    users = ensure_demo_users(db)
    maker = users["manufacturer"]
    for i in range(1, count + 1):
        name, category, manufacturer = rng.choice(PRODUCT_NAMES)
        data = {
            "name": f"{manufacturer} {name}",
            "model": f"{category[:2].upper()}-{rng.randint(100, 999)}",
            "category": category,
            "lifespan_years": rng.randint(3, 10),
            "spare_parts_percent": rng.choice([None, 20, 40, 60, 80, 95]),
            "materials": random_materials(rng),
        }
        product = repo.build_product(data)  # same validation as the API
        row = repo.insert_product(db, product, maker)
        repo.append_event(db, row, maker, "registered", "Passport created (synthetic demo data)")
        repo.append_event(db, row, maker, "manufactured", f"Manufactured by {manufacturer}")
        if rng.random() < 0.8:
            repo.append_event(db, row, users["consumer"], "sold", "Sold to first owner")
        for _ in range(rng.randint(0, 2)):
            repo.append_event(db, row, users["consumer"], "repaired", "Repair recorded")
        if rng.random() < 0.15:
            repo.append_event(db, row, users["recycler"], "recycled", "Sent to recycling")
        if i % batch == 0:
            db.commit()
    db.commit()
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--database", default=None, help="SQLite file (default: $DATABASE_PATH or passport.db)")
    args = parser.parse_args()
    start = time.perf_counter()
    with Database(args.database).connection() as db:
        seed(db, args.count)
    print(f"Added {args.count} products in {time.perf_counter() - start:.1f} s.")
    print("Demo logins (password for all: %s):" % DEMO_PASSWORD)
    for email, role in DEMO_USERS.items():
        print(f"  {role:<13} {email}")


if __name__ == "__main__":
    main()
