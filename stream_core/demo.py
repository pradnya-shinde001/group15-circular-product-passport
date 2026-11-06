"""Runs the full pipeline with all four subsystems.  Run:  python -m stream_core.demo"""

from stream_core import EventStream
from subsystem1_passport import MaterialComponent, Passport, Product, User
from subsystem1_passport.stream_steps import PassportHistoryStep, RegisteredProductFilter
from subsystem2_ledger import EventHasher, EventLedger, LifecycleEvent
from subsystem2_ledger.stream_filters import SequenceFilter, VerifiedEventFilter
from subsystem3_score.stream_transforms import (RecyclabilityIndexTransform, RemainingLifeTransform,
                                                RepairabilityTransform)
from subsystem4_ai_engine.stream_advice import AdviceTransform


def make_product(name):
    product = Product(name, "laptop", lifespan_years=6)
    product.add_material(MaterialComponent("aluminium", 60, recycled=True))
    product.add_material(MaterialComponent("plastic", 30))
    product.add_material(MaterialComponent("lithium battery", 10, hazard=True))
    return product


def make_fake_event(uuid, event_type, date, previous_hash, event_hash=None):
    """Build an event that is not saved in the ledger. It gets a correct hash unless one is given."""
    event = LifecycleEvent(uuid, event_type, "someone@example.com", {"date": date}, previous_hash)
    event.set_event_hash(event_hash or EventHasher().calculate_hash(event))
    return event


def main():
    # People and products
    maker = User("maker@example.com", role="manufacturer")
    owner = User("owner@example.com", role="consumer")
    recycler = User("recycler@example.com", role="recycler")

    laptop = make_product("EcoBook 14")
    tablet = make_product("EcoTab 10")
    products = {laptop.get_uuid(): laptop, tablet.get_uuid(): tablet}
    passports = {uuid: Passport(product) for uuid, product in products.items()}

    # Good events, saved in the ledger
    ledger = EventLedger()
    made = ledger.add_event(laptop, maker, "manufactured", {"date": "2020-01-15"})
    sold = ledger.add_event(laptop, maker, "sold", {"date": "2020-02-01"})
    used = ledger.add_event(laptop, owner, "used", {"date": "2021-01-10"})
    repaired = ledger.add_event(laptop, owner, "repaired", {"date": "2023-03-10"})
    refurbished = ledger.add_event(laptop, recycler, "refurbished", {"date": "2024-06-01"})
    recycled = ledger.add_event(laptop, recycler, "recycled", {"date": "2026-02-20"})

    # Bad events
    forged = make_fake_event(laptop.get_uuid(), "repaired", "2022-01-01", used.get_event_hash(), "forged-hash")
    too_early = make_fake_event(laptop.get_uuid(), "repaired", "2019-06-01", used.get_event_hash())
    no_passport = make_fake_event("unknown-id", "manufactured", "2020-01-01", "GENESIS")
    tablet_sold = ledger.add_event(tablet, maker, "sold", {"date": "2021-05-01"})   # never manufactured

    events = [made, sold, used, forged, too_early, sold, no_passport,   # sold is sent twice
              repaired, refurbished, recycled, tablet_sold]

    # Build the pipeline with |
    # CONCEPT: operator overloading. Each | calls __or__, which returns a Pipeline.
    # CONCEPT: abstract base classes. Each step below implements the abstract method of its parent.
    # CONCEPT: inheritance. The filters inherit from FilterProcessor (they implement keep()),
    #          and the transforms inherit from TransformProcessor (they implement transform()).
    pipeline = (RegisteredProductFilter(passports)       # FilterProcessor
                | VerifiedEventFilter()                  # FilterProcessor
                | SequenceFilter()                       # FilterProcessor
                | RecyclabilityIndexTransform(products)  # TransformProcessor
                | RemainingLifeTransform(products)       # TransformProcessor
                | RepairabilityTransform()               # TransformProcessor
                | AdviceTransform()                      # TransformProcessor
                | PassportHistoryStep(passports))        # TransformProcessor

    # Run it: events come out one at a time
    print(f"Events in: {len(events)}\n")
    count = 0
    # CONCEPT: iterator. Pipeline.run() loops over EventStream, which calls __iter__ and __next__.
    # CONCEPT: generator. run() uses yield, so this loop gets one finished record at a time.
    # CONCEPT: polymorphism. For each event, Pipeline.process() calls step.process() on every
    #          step in the same way, and each kind of step behaves differently.
    for record in pipeline.run(EventStream(events)):
        count += 1
        print(f"{record['event'].get_event_type():<13} {record['date']}  "
              f"Recyclability: {record['recyclability_index']:<6} "
              f"Life left: {record['life_left']:<7} Advice: {record['advice']}")
    print(f"\nEvents out: {count}")


if __name__ == "__main__":
    main()
