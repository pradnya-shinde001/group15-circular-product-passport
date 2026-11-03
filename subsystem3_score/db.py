"""Database helper: schema migration, new products, lifecycle events (+ automatic score recalculation)."""
import random
import sqlite3
from datetime import date

import score_store
from circularity import ScoreCalculator
from hash_manager import compute_event_hash

DB = "product_passport.db"

# Columns added by the upgrades. Old databases are migrated automatically.
NEW_COLUMNS = {
    "data_source": "TEXT DEFAULT 'synthetic'",
    "image_url": "TEXT",
    "external_ref": "TEXT",
    "spare_parts_availability": "INTEGER",    # 0-100, used by the repairability sub-score
    "hazardous_materials_count": "INTEGER",   # number of hazardous substances, used by the penalty
}

EVENT_TYPES = ["Used", "Repair", "Reuse", "Refurbish", "Ownership transfer", "End-of-Life"]


def connect(db_path=DB):
    return sqlite3.connect(db_path)


def synthetic_extras(product_id, repairability):
    """Deterministic synthetic values for the two new score inputs (same ID -> same values)."""
    rng = random.Random(f"extras-{product_id}")
    spare_parts = max(20, min(100, int(repairability) + rng.randint(-15, 15)))
    hazardous = rng.choices([0, 1, 2, 3], weights=[50, 30, 15, 5])[0]
    return spare_parts, hazardous


def ensure_schema(db_path=DB):
    """Migrate an older database: add columns, fill synthetic values, create the score table."""
    conn = connect(db_path)
    existing = {r[1] for r in conn.execute("PRAGMA table_info(products)")}
    for col, ddl in NEW_COLUMNS.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE products ADD COLUMN {col} {ddl}")
    conn.execute("UPDATE products SET data_source='synthetic' WHERE data_source IS NULL")
    # Only synthetic rows are auto-filled. Real products with unknown values stay NULL -> 'incomplete'.
    rows = conn.execute(
        "SELECT product_id, repairability_score FROM products WHERE data_source='synthetic' "
        "AND (spare_parts_availability IS NULL OR hazardous_materials_count IS NULL)").fetchall()
    for pid, rep in rows:
        sp, hz = synthetic_extras(pid, rep)
        conn.execute("UPDATE products SET spare_parts_availability=COALESCE(spare_parts_availability,?), "
                     "hazardous_materials_count=COALESCE(hazardous_materials_count,?) WHERE product_id=?",
                     (sp, hz, pid))
    score_store.ensure_table(conn)
    conn.commit()
    conn.close()


def next_product_id(conn):
    row = conn.execute(
        "SELECT MAX(CAST(SUBSTR(product_id, 4) AS INTEGER)) FROM products"
    ).fetchone()
    return f"EP-{(row[0] or 0) + 1:04d}"


def add_product(data, db_path=DB, calculator=None):
    """Insert a user-verified product, start its SHA-256 lifecycle chain and store its first score.

    Optional keys (None = unknown -> the score is flagged 'incomplete'):
    spare_parts_availability, hazardous_materials_count, image_url, external_ref.
    Returns the new product ID.
    """
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        score_store.ensure_table(conn)
        pid = next_product_id(conn)
        conn.execute(
            """INSERT INTO products
               (product_id, product_name, category, manufacturer, manufacturing_year,
                recycled_material_percent, repairability_score, reusability_score,
                recyclability_score, expected_lifetime_years, repair_count,
                current_condition, battery_recyclable, data_source, image_url, external_ref,
                spare_parts_availability, hazardous_materials_count)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                pid, data["product_name"], data["category"], data["manufacturer"],
                int(data["manufacturing_year"]), int(data["recycled_material_percent"]),
                int(data["repairability_score"]), int(data["reusability_score"]),
                int(data["recyclability_score"]), int(data["expected_lifetime_years"]),
                int(data["repair_count"]), data["current_condition"],
                int(data["battery_recyclable"]), data.get("data_source", "user-verified"),
                data.get("image_url"), data.get("external_ref"),
                data.get("spare_parts_availability"), data.get("hazardous_materials_count"),
            ),
        )

        today = date.today().isoformat()
        events = [
            (f"{int(data['manufacturing_year'])}-01-01", "Manufactured",
             "Product manufactured (only the year is known; date approximate)"),
            (today, "Registered",
             f"Passport created from verified information ({data.get('data_source', 'user-verified')})"),
        ]
        prev = ""
        for event_date, etype, desc in events:
            h = compute_event_hash(pid, event_date, etype, desc, prev)
            conn.execute(
                """INSERT INTO lifecycle_events
                   (product_id,event_date,event_type,description,event_hash,previous_hash)
                   VALUES (?,?,?,?,?,?)""",
                (pid, event_date, etype, desc, h, prev),
            )
            prev = h

        calculator = calculator or ScoreCalculator.with_defaults()
        product = dict(conn.execute("SELECT * FROM products WHERE product_id=?", (pid,)).fetchone())
        score_store.save_records(conn, [calculator.calculate(product).to_record("created")])
        conn.commit()
        return pid
    finally:
        conn.close()


def add_lifecycle_event(product_id, event_type, description, event_date=None,
                        db_path=DB, calculator=None):
    """Append an event to the SHA-256 chain, then AUTOMATICALLY recalculate and store the score (FR 7).

    A 'Repair' event also increases the product's repair_count.
    Returns the new CircularityScore.
    """
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        score_store.ensure_table(conn)
        if conn.execute("SELECT 1 FROM products WHERE product_id=?", (product_id,)).fetchone() is None:
            raise ValueError(f"Unknown product {product_id}")

        last = conn.execute(
            "SELECT event_hash FROM lifecycle_events WHERE product_id=? ORDER BY event_id DESC LIMIT 1",
            (product_id,)).fetchone()
        prev = last[0] if last else ""
        event_date = event_date or date.today().isoformat()
        h = compute_event_hash(product_id, event_date, event_type, description, prev)
        conn.execute(
            """INSERT INTO lifecycle_events
               (product_id,event_date,event_type,description,event_hash,previous_hash)
               VALUES (?,?,?,?,?,?)""",
            (product_id, event_date, event_type, description, h, prev),
        )
        if event_type == "Repair":
            conn.execute("UPDATE products SET repair_count = COALESCE(repair_count,0) + 1 WHERE product_id=?",
                         (product_id,))

        calculator = calculator or ScoreCalculator.with_defaults()
        product = dict(conn.execute("SELECT * FROM products WHERE product_id=?", (product_id,)).fetchone())
        score = calculator.calculate(product)
        score_store.save_records(conn, [score.to_record(f"event:{event_type}")])
        conn.commit()
        return score
    finally:
        conn.close()
