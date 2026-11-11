"""Subsystem 4 data in the shared database. Reads a product and its latest score;
writes the ai_predictions table, which keeps every recommendation."""
import json
from datetime import datetime

from database import connect

from .ai_prediction import AIPrediction


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
                "INSERT INTO ai_predictions (product_uuid, action, reason, source, model, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (product_uuid, prediction.get_action(), prediction.get_reason(), prediction.get_source(),
                 prediction.get_model(), prediction.get_created_at()))
            return cursor.lastrowid

    def get(self, prediction_id):
        """One saved recommendation as an AIPrediction object, or None when there is no such id."""
        with connect() as conn:
            row = conn.execute("SELECT * FROM ai_predictions WHERE id = ?", (prediction_id,)).fetchone()
        if row is None:
            return None
        prediction = AIPrediction(row["action"], row["reason"], row["source"], row["model"], row["rating"])
        prediction.set_created_at(row["created_at"])
        return prediction

    def add_identification(self, result):
        """Save the best category and material of one photo, and the model that found them (NFR 9)."""
        category = result["categories"][0]
        material = result["materials"][0]
        with connect() as conn:
            conn.execute(
                "INSERT INTO photo_identifications (category, category_confidence, material, material_confidence,"
                " model, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (category["label"], category["confidence"], material["label"], material["confidence"],
                 result["model"], datetime.now().isoformat(timespec="seconds")))

    def identifications(self):
        """All saved photo identifications, newest first."""
        with connect() as conn:
            rows = conn.execute("SELECT * FROM photo_identifications ORDER BY id DESC").fetchall()
        return [dict(row) for row in rows]

    def save_rating(self, prediction_id, rating):
        with connect() as conn:
            conn.execute("UPDATE ai_predictions SET rating = ? WHERE id = ?", (rating, prediction_id))

    def history(self, product_uuid):
        """All recommendations for a product, newest first."""
        with connect() as conn:
            rows = conn.execute("SELECT * FROM ai_predictions WHERE product_uuid = ? ORDER BY id DESC",
                                (product_uuid,)).fetchall()
        return [dict(row) for row in rows]
