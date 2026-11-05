
import uuid as uuid_lib

from .material_component import MaterialComponent

REQUIRED_FIELDS = ("name", "category", "lifespan_years", "materials")


class Product:
    def __init__(self, name, category, lifespan_years, model="", owner=None,
                 spare_parts_percent=None, uuid=None):
        """Constructor. `uuid` is only passed when a stored product is loaded again."""
        self._uuid = None
        self._name = None
        self._model = ""
        self._category = None
        self._lifespan_years = None
        self._spare_parts_percent = None
        self._owner = None
        self._materials = []
        self.initialize(name, category, lifespan_years, model, owner, spare_parts_percent, uuid)

    def initialize(self, name, category, lifespan_years, model, owner,
                   spare_parts_percent=None, uuid=None):
        """Initialization method: assigns a unique UUID and sets the fields."""
        self._uuid = str(uuid_lib.UUID(str(uuid))) if uuid else str(uuid_lib.uuid4())
        self.set_name(name)
        self.set_category(category)
        self.set_lifespan_years(lifespan_years)
        self.set_model(model)
        self.set_spare_parts_percent(spare_parts_percent)
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

    def get_spare_parts_percent(self):
        return self._spare_parts_percent

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
        if isinstance(years, bool) or not isinstance(years, (int, float)) or not 0 < years <= 100:
            raise ValueError("Lifespan must be a positive number of years (at most 100).")
        self._lifespan_years = years

    def set_spare_parts_percent(self, percent):
     
        if percent is None:
            self._spare_parts_percent = None
            return
        if isinstance(percent, bool) or not isinstance(percent, (int, float)) or not 0 <= percent <= 100:
            raise ValueError("Spare parts must be a number between 0 and 100.")
        self._spare_parts_percent = float(percent)

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
   
        return abs(self.total_percent() - 100.0) < 0.01

    def missing_fields(self):
       
        missing = []
        if not self._name:
            missing.append("name")
        if not self._category:
            missing.append("category")
        if not self._lifespan_years:
            missing.append("lifespan_years")
        if not self._materials:
            missing.append("materials")
        return missing

    @staticmethod
    def missing_in(data):
        missing = []
        for field in REQUIRED_FIELDS:
            value = data.get(field)
            if value is None or (isinstance(value, (str, list)) and not value) or \
                    (isinstance(value, str) and not value.strip()):
                missing.append(field)
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
