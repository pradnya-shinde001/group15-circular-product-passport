"""Subsystem 3 data in the shared database. Reads products, materials and repair events;
writes the circularity_scores table, which keeps every score so the history can be shown."""
import json

from database import connect


def _score(row):
    return {**dict(row), "sub_scores": json.loads(row["sub_scores"]), "missing": json.loads(row["missing"])}


class ScoreRepository:
    def product_data(self, product_uuid):
        """The product fields and materials the score needs, or None when there is no such product."""
        with connect() as conn:
            row = conn.execute("SELECT uuid, category, lifespan_years, spare_parts_percent FROM products"
                               " WHERE uuid = ?", (product_uuid,)).fetchone()
            if row is None:
                return None
            repairs = conn.execute("SELECT COUNT(*) FROM lifecycle_events WHERE product_uuid = ?"
                                   " AND event_type = 'repaired'", (product_uuid,)).fetchone()[0]
            materials = conn.execute("SELECT material, percent, recycled, recyclable, hazard"
                                     " FROM material_components WHERE product_uuid = ? ORDER BY id",
                                     (product_uuid,)).fetchall()
        product = {"product_id": row["uuid"], "category": row["category"],
                   "expected_lifetime_years": row["lifespan_years"],
                   "spare_parts_percent": row["spare_parts_percent"], "repair_count": repairs}
        # The passport stores "recycled" as yes or no, so a recycled material counts as a 100 % recycled share.
        return product, [{"material": m["material"], "percent": m["percent"], "recycled": 100 if m["recycled"] else 0,
                          "recyclable": bool(m["recyclable"]), "hazard": bool(m["hazard"])} for m in materials]

    def add(self, score, reason):
        """Save a CircularityScore object."""
        data = score.to_dict()
        with connect() as conn:
            cursor = conn.execute(
                "INSERT INTO circularity_scores (product_uuid, total, grade, sub_scores, missing, reason, computed_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (data["product_id"], data["total"], data["grade"], json.dumps(data["sub_scores"]),
                 json.dumps(data["missing"]), reason, data["computed_at"]))
            return cursor.lastrowid

    def latest(self, product_uuid):
        with connect() as conn:
            row = conn.execute("SELECT * FROM circularity_scores WHERE product_uuid = ? ORDER BY id DESC LIMIT 1",
                               (product_uuid,)).fetchone()
        return _score(row) if row else None

    def history(self, product_uuid):
        """All scores of a product, oldest first."""
        with connect() as conn:
            rows = conn.execute("SELECT * FROM circularity_scores WHERE product_uuid = ? ORDER BY id",
                                (product_uuid,)).fetchall()
        return [_score(row) for row in rows]
