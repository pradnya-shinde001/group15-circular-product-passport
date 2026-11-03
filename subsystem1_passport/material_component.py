"""MaterialComponent: one material a product is made of (Product 1 --- * MaterialComponent)."""


class MaterialComponent:
    def __init__(self, material, percent, recycled=False, hazard=False):
        """Constructor."""
        self._material = None
        self._percent = None
        self._recycled = False
        self._hazard = False
        self.initialize(material, percent, recycled, hazard)

    def initialize(self, material, percent, recycled, hazard):
        """Initialization method."""
        self.set_material(material)
        self.set_percent(percent)
        self.set_recycled(recycled)
        self.set_hazard(hazard)

    # ---- getters ----
    def get_material(self):
        return self._material

    def get_percent(self):
        return self._percent

    def is_recycled(self):
        return self._recycled

    def is_hazard(self):
        return self._hazard

    # ---- setters ----
    def set_material(self, material):
        if not isinstance(material, str) or not material.strip():
            raise ValueError("Material name is required.")
        self._material = material.strip()

    def set_percent(self, percent):
        if not isinstance(percent, (int, float)) or not 0 < percent <= 100:
            raise ValueError("Percent must be a number between 0 and 100.")
        self._percent = float(percent)

    def set_recycled(self, recycled):
        self._recycled = bool(recycled)

    def set_hazard(self, hazard):
        self._hazard = bool(hazard)

    def to_dict(self):
        return {
            "material": self._material,
            "percent": self._percent,
            "recycled": self._recycled,
            "hazard": self._hazard,
        }

    def __repr__(self):
        return f"MaterialComponent({self._material!r}, {self._percent}%)"
