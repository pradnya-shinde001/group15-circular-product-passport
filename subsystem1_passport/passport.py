"""Passport: the public page data for one product (Product 1 --- 1 Passport)."""
import json

from .qr_code import QRCode


class Passport:
    def __init__(self, product, base_url="http://localhost:8000"):
        """Constructor."""
        self._product = None
        self._public_url = None
        self._qr_code = None
        self._history = []
        self._score = None
        self.initialize(product, base_url)

    def initialize(self, product, base_url):
        """Initialization method: validates the product and builds the public URL (FR 3).
        The QR code is created the first time it is needed (see get_qr_code)."""
        product.validate()
        self._product = product
        self.set_public_url(f"{base_url.rstrip('/')}/passport/{product.get_uuid()}")

    # ---- getters ----
    def get_product(self):
        return self._product

    def get_public_url(self):
        return self._public_url

    def get_qr_code(self):
        """FR 3: the QR code that links to the public page, generated on first use."""
        if self._qr_code is None:
            self._qr_code = QRCode(self._public_url)
        return self._qr_code

    def get_history(self):
        return list(self._history)

    def get_score(self):
        return self._score

    # ---- setters ----
    def set_public_url(self, url):
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            raise ValueError("Public URL must start with http:// or https://")
        self._public_url = url
        self._qr_code = None  # the old code points to the old URL

    def set_score(self, score):
        """FR 9: the circularity score as a dict (from Subsystem 3), or None."""
        if score is not None and not isinstance(score, dict):
            raise TypeError("Score must be a dict or None.")
        self._score = score

    def add_history_event(self, event):
        """History entries are only added, never deleted (NFR 7).
        `event` is a description string or a dict (e.g. from the history table)."""
        if isinstance(event, str):
            event = {"event_type": "note", "details": event}
        if not isinstance(event, dict):
            raise TypeError("A history event must be a string or a dict.")
        self._history.append(dict(event))

    # ---- behaviour ----
    def to_dict(self):
        p = self._product
        return {
            "uuid": p.get_uuid(),
            "name": p.get_name(),
            "model": p.get_model(),
            "category": p.get_category(),
            "lifespan_years": p.get_lifespan_years(),
            "spare_parts_percent": p.get_spare_parts_percent(),
            "materials": [m.to_dict() for m in p.get_materials()],
            "public_url": self._public_url,
            "qr_code_url": f"{self._public_url}/qr.png",
            "circularity_score": self._score,
            "history": self.get_history(),
        }

    def export_json(self):
        """FR 10: the passport as JSON, ready for a REST response."""
        return json.dumps(self.to_dict(), indent=2)
