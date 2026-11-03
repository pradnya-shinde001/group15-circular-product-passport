
from subsystem1_passport import Product, User

from .chain_verifier import ChainVerifier
from .event_hasher import EventHasher
from .event_ledger import EventLedger


def notify_score_engine(event):
    print(f"[Score Engine] Notified about: {event.get_event_type()}")


def display_event(event, number, previous_event, hasher):

    print(f"\n--- Lifecycle Event {number}: {event.get_event_type().upper()} ---")

    print("[LifecycleEvent]")
    print(f"Product UUID : {event.get_product_uuid()}")
    print(f"Event Type   : {event.get_event_type()}")
    print(f"Timestamp    : {event.get_timestamp()}")
    print(f"Actor        : {event.get_actor_email()}")
    print(f"Details      : {event.get_details()}")

    expected_hash = "GENESIS" if previous_event is None else previous_event.get_event_hash()

    previous_match = event.get_previous_hash() == expected_hash
    current_match = hasher.verify_hash(event)

    print("\n[EventHasher]")
    print(f"Previous Hash       : {event.get_previous_hash()}")
    print(f"Current Event Hash  : {event.get_event_hash()}")
    print(f"Previous Hash Match : {'PASS' if previous_match else 'FAIL'}")
    print(f"Current Hash Match  : {'PASS' if current_match else 'FAIL'}")


def main():

    manufacturer = User("manufacturer@example.com", role="manufacturer", password="demo1234")
    consumer = User("consumer@example.com", role="consumer", password="demo1234")
    recycler = User("recycler@example.com", role="recycler", password="demo1234")

    product = Product(
        "EcoBook 14",
        "laptop",
        lifespan_years=6,
        model="EB-14",
        owner=manufacturer
    )

    print("\n[EventLedger] Initializing event ledger.")
    ledger = EventLedger(score_engine_callback=notify_score_engine)

    print("[EventHasher] Initializing SHA-256 hasher.")
    hasher = EventHasher()

    print("[ChainVerifier] Initializing chain verifier.")
    verifier = ChainVerifier(ledger.get_genesis_hash())

    lifecycle_events = [
        (manufacturer, "manufactured", {"factory": "Germany", "model": "EB-14"}),
        (manufacturer, "sold", {"price": 1200, "currency": "EUR"}),
        (consumer, "used", {"description": "Product put into use"}),
        (consumer, "repaired", {"description": "Battery replaced"}),
        (recycler, "refurbished", {"description": "Product refurbished for reuse"}),
        (recycler, "recycled", {"description": "Material recovery"})
    ]

    previous_event = None

    for number, (actor, event_type, details) in enumerate(lifecycle_events, start=1):

        print(f"\n[EventLedger] Recording {event_type.upper()} event.")

        event = ledger.add_event(product, actor, event_type, details)

        display_event(event, number, previous_event, hasher)

        previous_event = event

    history = ledger.get_history(product.get_uuid())

    print("\n[ChainVerifier] Verifying complete lifecycle hash chain.")

    result = verifier.verify_chain(history)

    print(f"Total Events       : {len(history)}")
    print(f"Chain Verification : {'PASS' if result['valid'] else 'FAIL'}")
    print(f"First Broken Event : {result['first_broken_event']}")

    if result["valid"]:
        print("Result: All lifecycle events passed integrity verification.")


if __name__ == "__main__":
    main()
