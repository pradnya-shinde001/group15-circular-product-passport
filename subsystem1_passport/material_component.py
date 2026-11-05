class MaterialComponent:
    def __init__(self, material, percent, recycled=False, hazard=False, recyclable=True):
        """Constructor.

        recycled: True/False, or the recycled share of this material in % (0-100).
        True counts as 100 % recycled, False as 0 %.
        """
        self._material = None
        self._percent = None
        self._recycled_share = 0.0
        self._hazard = False
        self._recyclable = True
        self.initialize(material, percent, recycled, hazard, recyclable)

    def initialize(self, material, percent, recycled, hazard, recyclable=True):
        """Initialization method."""
        self.set_material(material)
        self.set_percent(percent)
        self.set_recycled(recycled)
        self.set_hazard(hazard)
        self.set_recyclable(recyclable)

    # ---- getters ----
    def get_material(self):
        return self._material

    def get_percent(self):
        return self._percent

    def get_recycled_share(self):
        return self._recycled_share

    def is_recycled(self):
        return self._recycled_share > 0

    def is_hazard(self):
        return self._hazard

    def is_recyclable(self):
        return self._recyclable

    # ---- setters ----
    def set_material(self, material):
        if not isinstance(material, str) or not material.strip():
            raise ValueError("Material name is required.")
        self._material = material.strip()

    def set_percent(self, percent):
        if isinstance(percent, bool) or not isinstance(percent, (int, float)) or not 0 < percent <= 100:
            raise ValueError("Percent must be a number between 0 and 100.")
        self._percent = float(percent)

    def set_recycled(self, recycled):
        if isinstance(recycled, bool):
            self._recycled_share = 100.0 if recycled else 0.0
            return
        if not isinstance(recycled, (int, float)) or not 0 <= recycled <= 100:
            raise ValueError("Recycled share must be True/False or a number between 0 and 100.")
        self._recycled_share = float(recycled)

    def set_hazard(self, hazard):
        self._hazard = bool(hazard)

    def set_recyclable(self, recyclable):
        self._recyclable = bool(recyclable)

    def to_dict(self):
        return {
            "material": self._material,
            "percent": self._percent,
            "recycled": self._recycled_share,
            "recyclable": self._recyclable,
            "hazard": self._hazard,
        }

    def __repr__(self):
        return f"MaterialComponent({self._material!r}, {self._percent}%)"
