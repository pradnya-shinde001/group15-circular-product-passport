# AI-Powered Circular Economy Product Passport

Group 15, Capstone Project, FH Dortmund. A digital passport for electronic products: a unique QR-based identity, a tamper-evident lifecycle history, a circularity score, and AI identification and advice.

Each homework assignment has its own branch. The classes are added there.

## Team Overview

| Team member        | Subsystem                                | Folder                                        |
| ------------------ | ---------------------------------------- | --------------------------------------------- |
| Mosaddeka Mallick  | 1. Passport, QR code and web UI          | [subsystem1_passport](subsystem1_passport/)   |
| Anishkumar Sukumar | 2. Event ledger (tamper-evident history) | [subsystem2_ledger](subsystem2_ledger/)       |
| Rajib Munshi       | 3. Circularity score engine              | [subsystem3_score](subsystem3_score/)         |
| Pradnya Shinde     | 4. AI engine (identification and advice) | [subsystem4_ai_engine](subsystem4_ai_engine/) |

## Presentation Link

**Team video:** the link will be added here.

## System Design

### Subsystem 1: Passport, QR code and web UI

### Classes: `User`, `Product`, `MaterialComponent`, `Passport`, `QRCode`.

```mermaid
classDiagram
    User "1" --> "*" Product : owns
    Product "1" --> "1" Passport : has
    Product "1" --> "*" MaterialComponent : made of
    Passport "1" --> "1" QRCode : has
    class User {
        -email
        -role
        -password_hash
        +get_email()
        +set_email()
        +get_role()
        +set_role()
        +set_password()
        +check_password()
        +can_edit()
    }
    class Product {
        -uuid
        -name
        -model
        -category
        -lifespan_years
        +get_name()
        +set_name()
        +add_material()
        +materials_valid()
        +validate()
    }
    class MaterialComponent {
        -material
        -percent
        -recycled
        -hazard
        +get_percent()
        +set_percent()
        +to_dict()
    }
    class Passport {
        -public_url
        +get_public_url()
        +set_public_url()
        +export_json()
    }
    class QRCode {
        -png_bytes
        -target_url
        +get_target_url()
        +set_target_url()
        +generate()
        +save()
    }
```

### Subsystem 2: Event Ledger (Tamper-Evident History)

**Classes:** `LifecycleEvent`, `EventLedger`, `ChainVerifier`.

```mermaid
classDiagram
    Product "1" --> "*" LifecycleEvent : has
    User "1" --> "*" LifecycleEvent : creates
    EventLedger "1" --> "*" LifecycleEvent : manages
    ChainVerifier ..> LifecycleEvent : verifies

    class Product {
        <<external>>
        -uuid
    }

    class User {
        <<external>>
        -id
        -role
    }

    class LifecycleEvent {
        -product_id
        -event_type
        -timestamp
        -actor_id
        -details
        -previous_hash
        -event_hash
        +__init__()
        +calculate_hash()
        +get_event_data()
        +get_event_hash()
        +get_event_type()
        +set_details()
    }

    class EventLedger {
        -events
        -genesis_hash
        +__init__()
        +initialize()
        +add_event()
        +get_history()
        +get_events()
    }

    class ChainVerifier {
        -genesis_hash
        +__init__()
        +verify_chain()
        +first_broken_event()
        +get_result()
    }
```
### Subsystem 3: Circularity score engine

TODO

### Subsystem 4: AI engine

```mermaid
classDiagram
    ImageClassifier "1" --> "*" AIPrediction : makes
    AIPrediction "*" --> "1" Recommender : by
    Recommender "1" --> "1" RuleBasedAdvisor : falls back to
    Recommender "1" --> "1" LLMAdapter : uses
    class ImageClassifier {
        CLIP model
        classify(photo)
    }
    class AIPrediction {
        kind
        result
        version
        rating
    }
    class Recommender {
        reason
        recommend(product)
    }
    class RuleBasedAdvisor {
        fallback
        advise(product)
    }
    class LLMAdapter {
        swappable
        complete(prompt)
    }
```
