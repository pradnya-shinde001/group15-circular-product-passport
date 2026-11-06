"""Subsystem 4 data in the shared database. Reads a product and its latest score;
writes the ai_predictions table, which keeps every recommendation."""
import json

from database import connect


class RecommendationRepository:
    def product_data(self, product_uuid):
        """What the Recommender needs about one product, or None when there is no such product."""
        with connect() as conn:
            product = conn.execute("SELECT name, category, condition FROM products WHERE uuid = ?",
                                   (product_uuid,)).fetchone()
            score = conn.execute("SELECT total, sub_scores FROM circularity_scores WHERE product_uuid = ?"
                                 " ORDER BY id DESC LIMIT 1", (product_uuid,)).fetchone()
        if product is None:
            return None

        # Take the total and the repairability sub-score from the latest score. Without a score, both are 0.
        total = 0
        repairability = 0
        if score is not None:
            total = score["total"]
            for sub_score in json.loads(score["sub_scores"]):
                if sub_score["name"] == "repairability" and sub_score["value"] is not None:
                    repairability = sub_score["value"]

        # The circularity score stands in for reusability until the product data has its own field.
        return {"name": product["name"], "category": product["category"], "condition": product["condition"],
                "repairability_score": repairability, "reusability_score": total}

    def add(self, product_uuid, prediction):
        """Save an AIPrediction object."""
        with connect() as conn:
            cursor = conn.execute(
                "INSERT INTO ai_predictions (product_uuid, action, reason, source, created_at) VALUES (?, ?, ?, ?, ?)",
                (product_uuid, prediction.get_action(), prediction.get_reason(), prediction.get_source(),
                 prediction.get_created_at()))
            return cursor.lastrowid

    def history(self, product_uuid):
        """All recommendations for a product, newest first."""
        with connect() as conn:
            rows = conn.execute("SELECT * FROM ai_predictions WHERE product_uuid = ? ORDER BY id DESC",
                                (product_uuid,)).fetchall()
        return [dict(row) for row in rows]
