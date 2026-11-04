"""Product: the registered item (UML: Product has uuid, name, model, category, lifespan)."""
import uuid as uuid_lib

from .material_component import MaterialComponent


class Product:
    def __init__(self, name, category, lifespan_years, model="", owner=None):
        """Constructor."""
        self._uuid = None
        self._name = None
        self._model = ""
        self._category = None
        self._lifespan_years = None
        self._owner = None
        self._materials = []
        self.initialize(name, category, lifespan_years, model, owner)

    def initialize(self, name, category, lifespan_years, model, owner):
        """Initialization method: assigns a unique UUID (FR 2) and sets the fields."""
        self._uuid = str(uuid_lib.uuid4())
        self.set_name(name)
        self.set_category(category)
        self.set_lifespan_years(lifespan_years)
        self.set_model(model)
        if owner is not None:
            self.set_owner(owner)

    # ---- getters ----
    def get_uuid(self):
        return self._uuid

    def get_name(self):
        return self._name

    def get_model(self):
        return self._model

    def get_category(self):
        return self._category

    def get_lifespan_years(self):
        return self._lifespan_years

    def get_owner(self):
        return self._owner

    def get_materials(self):
        return list(self._materials)

    # ---- setters (the UUID has no setter: it must never change, NFR 7) ----
    def set_name(self, name):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Product name is required.")
        self._name = name.strip()

    def set_model(self, model):
        self._model = (model or "").strip()

    def set_category(self, category):
        if not isinstance(category, str) or not category.strip():
            raise ValueError("Product category is required.")
        self._category = category.strip()

    def set_lifespan_years(self, years):
        if not isinstance(years, (int, float)) or years <= 0:
            raise ValueError("Lifespan must be a positive number of years.")
        self._lifespan_years = years

    def set_owner(self, user):
        self._owner = user
        user.add_product(self)

    # ---- behaviour ----
    def add_material(self, component):
        if not isinstance(component, MaterialComponent):
            raise TypeError("Expected a MaterialComponent.")
        self._materials.append(component)

    def total_percent(self):
        return sum(m.get_percent() for m in self._materials)

    def materials_valid(self):
        """FR 5: material percentages must sum to 100 %."""
        return abs(self.total_percent() - 100.0) < 0.01

    def missing_fields(self):
        """FR 6: names every missing field of an incomplete registration."""
        missing = []
        if not self._name:
            missing.append("name")
        if not self._category:
            missing.append("category")
        if not self._lifespan_years:
            missing.append("lifespan")
        if not self._materials:
            missing.append("materials")
        return missing

    def validate(self):
        missing = self.missing_fields()
        if missing:
            raise ValueError("Registration incomplete, missing: " + ", ".join(missing))
        if not self.materials_valid():
            raise ValueError(
                f"Material percentages sum to {self.total_percent():.1f}%, expected 100%."
            )
        return True

    def __repr__(self):
        return f"Product({self._name!r}, uuid={self._uuid[:8]}...)"
