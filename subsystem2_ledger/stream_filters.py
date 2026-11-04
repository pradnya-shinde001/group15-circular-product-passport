"""Subsystem 2's pipeline steps."""
from stream_core import FilterProcessor

from .event_hasher import EventHasher
from .event_ledger import EventLedger


class VerifiedEventFilter(FilterProcessor):
    """Keeps an event only if its hash matches its contents."""

    reason = "unverified, hash does not match"

    def __init__(self):
        self.hasher = EventHasher()

    def keep(self, record):
        return self.hasher.verify_hash(record["event"])


class SequenceFilter(FilterProcessor):
    """Keeps an event only if it correctly follows the product's last accepted event."""

    reason = "out of sequence"

    def __init__(self):
        self.last_records = {}               # {product uuid: last accepted record}

    def keep(self, record):
        event = record["event"]
        uuid = event.get_product_uuid()
        event_type = event.get_event_type()
        last = self.last_records.get(uuid)

        if record["date"] is None:
            return False

        if last is None:
            in_order = (event_type == "manufactured"
                        and event.get_previous_hash() == EventLedger.GENESIS_HASH)
        else:
            in_order = (event_type != "manufactured"
                        and last["event"].get_event_type() != "recycled"
                        and event.get_previous_hash() == last["event"].get_event_hash()
                        and record["date"] >= last["date"])

        if in_order:
            self.last_records[uuid] = record
        return in_order
