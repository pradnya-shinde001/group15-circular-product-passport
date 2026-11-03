# Subsystem 2 – Event Ledger

## Overview

The Event Ledger subsystem manages and maintains the lifecycle history of products, from manufacturing to recycling. It records lifecycle events using SHA-256 hash chaining to make unauthorized modifications detectable.

## Implemented Classes

### 1. LifecycleEvent

Represents an individual product lifecycle event. It stores the product UUID, event type, UTC timestamp, actor email, event details and associated hashes.

- Supports six lifecycle event types: manufactured, sold, used, repaired, refurbished and recycled.
- Calculates a SHA-256 hash for each event.
- Maintains the previous event hash to establish the hash chain.
- Provides getters and setters for event attributes.
- Seals event data after initialization to prevent normal setter-based modifications.

### 2. EventLedger

Maintains and organizes the lifecycle event history for each product.

- Records and manages lifecycle events.
- Validates event types and user-role permissions.
- Maintains a separate hash chain for each product.
- Uses a genesis hash to start each product's event chain.
- Supports an optional callback to notify the score engine when a new event is recorded.

### 3. ChainVerifier

Verifies the integrity of the lifecycle event hash chain.

- Checks the connection between consecutive event hashes.
- Recalculates event hashes to detect modifications.
- Returns the verification result.
- Identifies the first broken event in the chain.

## Testing and Demonstration

The `test.py` file demonstrates the functionality of the Event Ledger subsystem using the actual `Product` and `User` classes from Subsystem 1.

The demonstration covers:

- Creating a product and users with different roles.
- Recording all six lifecycle event types.
- Displaying the product's lifecycle history.
- Verifying the integrity of the SHA-256 hash chain.
- Modifying an event's details to demonstrate tamper detection.

### Execution

Run the following command from the repository root:

```bash
python -m subsystem2_ledger.test
```

### Expected Results

- All six lifecycle events are recorded successfully.
- Initial chain verification returns `valid: True`.
- After modifying the second event, verification returns `valid: False`.
- The verifier identifies Event 2 as the first broken event.

**Integration:** Subsystem 2 imports `Product` and `User` from Subsystem 1. Both packages must be available from the repository root.

The tampering operation in `test.py` is performed only for demonstration purposes.