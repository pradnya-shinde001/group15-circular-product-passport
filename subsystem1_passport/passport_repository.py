"""Subsystem 1 data in the shared database: the users, products and material_components tables."""
from datetime import datetime, timezone

from database import connect


class UserRepository:
    def add(self, user):
        """Save a User object. Only its password hash is stored."""
        with connect() as conn:
            cursor = conn.execute("INSERT INTO users (email, role, password_hash) VALUES (?, ?, ?)",
                                  (user.get_email(), user.get_role(), user.get_password_hash()))
            return cursor.lastrowid

    def get(self, user_id):
        with connect() as conn:
            row = conn.execute("SELECT id, email, role FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None

    def all(self):
        with connect() as conn:
            rows = conn.execute("SELECT id, email, role FROM users ORDER BY id").fetchall()
        return [dict(row) for row in rows]


class ProductRepository:
    def add(self, product, materials, public_url, owner_id, spare_parts_percent, condition):
        """Save a validated Product and its materials in one transaction.
        `materials` are MaterialComponent.to_dict() results with an extra "recyclable" key."""
        with connect() as conn:
            conn.execute(
                "INSERT INTO products (uuid, name, model, category, lifespan_years, spare_parts_percent,"
                " condition, owner_id, public_url, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (product.get_uuid(), product.get_name(), product.get_model(), product.get_category(),
                 product.get_lifespan_years(), spare_parts_percent, condition, owner_id, public_url,
                 datetime.now(timezone.utc).isoformat(timespec="seconds")))
            conn.executemany(
                "INSERT INTO material_components (product_uuid, material, percent, recycled, recyclable, hazard)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                [(product.get_uuid(), m["material"], m["percent"], int(m["recycled"]), int(m["recyclable"]),
                  int(m["hazard"])) for m in materials])
        return product.get_uuid()

    def get(self, uuid):
        """One product with its owner's email, or None."""
        with connect() as conn:
            row = conn.execute("SELECT p.*, u.email AS owner_email FROM products p "
                               "LEFT JOIN users u ON u.id = p.owner_id WHERE p.uuid = ?", (uuid,)).fetchone()
        return dict(row) if row else None

    def materials(self, uuid):
        with connect() as conn:
            rows = conn.execute("SELECT material, percent, recycled, recyclable, hazard FROM material_components"
                                " WHERE product_uuid = ? ORDER BY id", (uuid,)).fetchall()
        return [{**dict(row), "recycled": bool(row["recycled"]), "recyclable": bool(row["recyclable"]),
                 "hazard": bool(row["hazard"])} for row in rows]

    def search(self, text=""):
        """Products whose name, model, category or UUID contains the text, with their latest grade."""
        like = f"%{text.strip()}%"
        with connect() as conn:
            rows = conn.execute(
                "SELECT p.uuid, p.name, p.model, p.category, s.total, s.grade FROM products p"
                " LEFT JOIN circularity_scores s ON s.id ="
                "   (SELECT MAX(id) FROM circularity_scores WHERE product_uuid = p.uuid)"
                " WHERE p.name LIKE ? OR p.model LIKE ? OR p.category LIKE ? OR p.uuid LIKE ?"
                " ORDER BY p.created_at DESC, p.name", (like, like, like, like)).fetchall()
        return [dict(row) for row in rows]
