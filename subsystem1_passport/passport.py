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
        self.initialize(product, base_url)

    def initialize(self, product, base_url):
        """Initialization method: validates the product, builds the URL and QR code (FR 3)."""
        product.validate()
        self._product = product
        self.set_public_url(f"{base_url.rstrip('/')}/passport/{product.get_uuid()}")
        self._qr_code = QRCode(self._public_url)

    # ---- getters ----
    def get_product(self):
        return self._product

    def get_public_url(self):
        return self._public_url

    def get_qr_code(self):
        return self._qr_code

    def get_history(self):
        return list(self._history)

    # ---- setters ----
    def set_public_url(self, url):
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            raise ValueError("Public URL must start with http:// or https://")
        self._public_url = url

    def add_history_event(self, description):
        """History entries are only added, never deleted (NFR 7)."""
        self._history.append(description)

    # ---- behaviour ----
    def export_json(self):
        """FR 10: the passport as JSON, ready for a REST response."""
        p = self._product
        return json.dumps(
            {
                "uuid": p.get_uuid(),
                "name": p.get_name(),
                "model": p.get_model(),
                "category": p.get_category(),
                "lifespan_years": p.get_lifespan_years(),
                "materials": [m.to_dict() for m in p.get_materials()],
                "public_url": self._public_url,
                "history": self._history,
            },
            indent=2,
        )
