
"""Run from the repo root: python -m subsystem2_ledger.test"""

from subsystem1_passport import Product, User
from subsystem2_ledger import ChainVerifier, EventLedger


def main():

    # Create users

    manufacturer = User(
        "manufacturer@example.com",
        role="manufacturer",
        password="s3cretPass!"
    )

    consumer = User(
        "consumer@example.com",
        role="consumer",
        password="consumerPass!"
    )

    recycler = User(
        "recycler@example.com",
        role="recycler",
        password="recyclerPass!"
    )

    # Create product

    laptop = Product(
        "EcoBook 14",
        "laptop",
        lifespan_years=6,
        model="EB-14",
        owner=manufacturer
    )

    # Create Event Ledger

    ledger = EventLedger()

    # Record lifecycle events

    ledger.add_event(
        laptop, manufacturer, "manufactured",
        {"location": "Germany", "condition": "New"}
    )

    ledger.add_event(
        laptop, consumer, "sold",
        {"price": 1200, "currency": "EUR"}
    )

    ledger.add_event(
        laptop, consumer, "used",
        {"condition": "Normal use"}
    )

    ledger.add_event(
        laptop, manufacturer, "repaired",
        {"repair": "Battery replaced"}
    )

    ledger.add_event(
        laptop, recycler, "refurbished",
        {"action": "Components refurbished"}
    )

    ledger.add_event(
        laptop, recycler, "recycled",
        {"action": "Material recovered"}
    )

    # Display product lifecycle history

    history = ledger.get_history(laptop.get_uuid())

    print("\n--- Product Lifecycle History ---")

    for index, event in enumerate(history, start=1):
        print(f"\nEvent {index}:")
        print("Type:", event.get_event_type())
        print("Timestamp:", event.get_timestamp())
        print("Actor:", event.get_actor_email())
        print("Details:", event.get_details())
        print("Previous Hash:", event.get_previous_hash())
        print("Event Hash:", event.get_event_hash())

    # Verify hash chain

    verifier = ChainVerifier()
    verifier.set_genesis_hash(ledger.get_genesis_hash())

    print("\n--- Chain Verification ---")

    result = verifier.verify_chain(history)
    print("Verification result:", result)

    # Demonstrate tamper detection

    print("\n--- Tamper Detection ---")

    history[1]._details["price"] = 1

    result = verifier.verify_chain(history)
    print("Verification result:", result)

    if not result["valid"]:
        print("Tampering detected at event:", verifier.first_broken_event())


if __name__ == "__main__":
    main()
