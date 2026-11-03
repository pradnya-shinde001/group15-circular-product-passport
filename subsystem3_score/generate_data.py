import sqlite3
import random
from datetime import date, timedelta
from pathlib import Path
import hashlib
from hash_manager import compute_event_hash
from db import synthetic_extras
from circularity import ScoreCalculator
import score_store

DB = Path("product_passport.db")

random.seed(42)

products = []
events = []

product_names = [
    ("ThinkPad Laptop", "Laptop", "Lenovo"),
    ("Galaxy Smartphone", "Smartphone", "Samsung"),
    ("UltraView Monitor", "Monitor", "Dell"),
    ("Pro Tablet", "Tablet", "Samsung"),
    ("Eco Laptop", "Laptop", "HP"),
    ("Office Monitor", "Monitor", "LG"),
]

materials = ["Aluminum", "Plastic", "Copper", "Glass", "Lithium"]
conditions = ["Excellent", "Good", "Fair", "Poor"]
end_options = ["Reuse", "Repair", "Refurbish", "Recycle"]

for i in range(1, 101):
    name, category, manufacturer = random.choice(product_names)
    pid = f"EP-{i:04d}"
    year = random.randint(2021, 2026)
    recycled = random.randint(10, 70)
    repairability = random.randint(35, 95)
    reusability = random.randint(35, 95)
    recyclability = random.randint(40, 95)
    lifetime = random.randint(3, 10)
    repair_count = random.randint(0, 4)
    condition = random.choice(conditions)
    battery_recyclable = random.choice([0, 1])

    spare_parts, hazardous = synthetic_extras(pid, repairability)
    products.append((
        pid, name, category, manufacturer, year, recycled,
        repairability, reusability, recyclability, lifetime,
        repair_count, condition, battery_recyclable,
        "synthetic", None, None, spare_parts, hazardous
    ))

    start = date(year, random.randint(1, 12), random.randint(1, 25))
    descriptions = [
        ("Manufactured", "Product manufactured"),
        ("Sold", "Product sold to first owner"),
        ("Used", "Product entered normal use"),
    ]
    if repair_count > 0:
        descriptions.append(("Repair", f"{repair_count} repair event(s) recorded"))
    if condition in ["Excellent", "Good"]:
        descriptions.append(("Reuse", "Product transferred for reuse"))
    descriptions.append(("End-of-Life", random.choice(end_options)))

    prev_hash = ""
    for j, (etype, desc) in enumerate(descriptions):
        event_date = start + timedelta(days=j * random.randint(120, 420))
        event_hash = compute_event_hash(pid, event_date, etype, desc, prev_hash)
        events.append((pid, event_date.isoformat(), etype, desc, event_hash, prev_hash))
        prev_hash = event_hash

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS circularity_scores")
cur.execute("DROP TABLE IF EXISTS lifecycle_events")
cur.execute("DROP TABLE IF EXISTS products")

cur.execute("""
CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    product_name TEXT,
    category TEXT,
    manufacturer TEXT,
    manufacturing_year INTEGER,
    recycled_material_percent INTEGER,
    repairability_score INTEGER,
    reusability_score INTEGER,
    recyclability_score INTEGER,
    expected_lifetime_years INTEGER,
    repair_count INTEGER,
    current_condition TEXT,
    battery_recyclable INTEGER,
    data_source TEXT DEFAULT 'synthetic',
    image_url TEXT,
    external_ref TEXT,
    spare_parts_availability INTEGER,
    hazardous_materials_count INTEGER
)
""")

cur.execute("""
CREATE TABLE lifecycle_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT,
    event_date TEXT,
    event_type TEXT,
    description TEXT,
    event_hash TEXT,
    previous_hash TEXT,
    FOREIGN KEY(product_id) REFERENCES products(product_id)
)
""")

cur.executemany("INSERT INTO products VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", products)
cur.executemany("""
INSERT INTO lifecycle_events
(product_id,event_date,event_type,description,event_hash,previous_hash)
VALUES (?,?,?,?,?,?)
""", events)

conn.commit()
conn.close()

stored = ScoreCalculator.with_defaults().recalculate_all(str(DB), trigger="initial")
print(f"Stored {stored} initial circularity scores.")
print(f"Created {DB} with {len(products)} products and {len(events)} lifecycle events.")
