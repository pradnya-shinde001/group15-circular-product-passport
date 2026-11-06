"""Subsystem 3's pipeline steps. The numbers here are team assumptions and easy to change."""
from stream_core import TransformProcessor

from .score_calculator import recyclability_score, repairability_score

RECYCLABLE_MATERIALS = ("aluminium", "steel", "copper", "glass", "lithium battery")
SPARE_PARTS_PERCENT = 50


class RecyclabilityIndexTransform(TransformProcessor):
    """Index = recyclable share of the materials + the effect of events so far (0 to 100)."""

    CHANGES = {"used": -1, "repaired": 2, "refurbished": 5}

    def __init__(self, products):
        self.products = products
        self.indexes = {}                    # {product uuid: current index}

    def starting_index(self, product):
        materials = [{"percent": m.get_percent(), "recyclable": m.get_material() in RECYCLABLE_MATERIALS}
                     for m in product.get_materials()]
        return recyclability_score(materials)

    def transform(self, record):
        event = record["event"]
        uuid = event.get_product_uuid()
        if uuid not in self.indexes:
            self.indexes[uuid] = self.starting_index(self.products[uuid])

        index = self.indexes[uuid] + self.CHANGES.get(event.get_event_type(), 0)
        self.indexes[uuid] = max(0, min(100, index))
        record["recyclability_index"] = self.indexes[uuid]


class RemainingLifeTransform(TransformProcessor):
    """Life left % = 100 - share of the lifespan used + bonuses from repairs (0 to 100)."""

    BONUSES = {"repaired": 5, "refurbished": 20}

    def __init__(self, products):
        self.products = products
        self.start_dates = {}                # {product uuid: first event's date}
        self.bonuses = {}                    # {product uuid: total bonus so far}

    def transform(self, record):
        event = record["event"]
        uuid = event.get_product_uuid()
        start = self.start_dates.setdefault(uuid, record["date"])
        self.bonuses[uuid] = self.bonuses.get(uuid, 0) + self.BONUSES.get(event.get_event_type(), 0)

        years_used = (record["date"] - start).days / 365.25
        used_percent = years_used / self.products[uuid].get_lifespan_years() * 100
        life_left = 100 - used_percent + self.bonuses[uuid]

        if event.get_event_type() == "recycled":
            life_left = 0
        record["life_left"] = round(max(0, min(100, life_left)), 1)


class RepairabilityTransform(TransformProcessor):
    """Counts repairs, and uses Subsystem 3's formula to work out the repairability score."""

    def __init__(self):
        self.repairs = {}                    # {product uuid: number of repairs}

    def transform(self, record):
        event = record["event"]
        uuid = event.get_product_uuid()
        if event.get_event_type() == "repaired":
            self.repairs[uuid] = self.repairs.get(uuid, 0) + 1
        record["repairability"] = repairability_score(SPARE_PARTS_PERCENT, self.repairs.get(uuid, 0))
