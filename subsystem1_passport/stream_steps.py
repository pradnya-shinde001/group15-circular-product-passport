"""Subsystem 1's pipeline steps."""
from stream_core import FilterProcessor, TransformProcessor


class RegisteredProductFilter(FilterProcessor):
    """Keeps an event only if its product has a passport."""

    reason = "product has no passport"

    def __init__(self, passports):
        self.passports = passports

    def keep(self, record):
        return record["event"].get_product_uuid() in self.passports


class PassportHistoryStep(TransformProcessor):
    """Writes each accepted event into the product's passport."""

    def __init__(self, passports):
        self.passports = passports

    def transform(self, record):
        event = record["event"]
        passport = self.passports[event.get_product_uuid()]
        passport.add_history_event(f"{record['date']}: {event.get_event_type()}")
