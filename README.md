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

### Subsystem 2: Event Ledger

**Classes:** LifecycleEvent, EventLedger, ChainVerifier

```mermaid
classDiagram

    Product "1" --> "*" LifecycleEvent : has
    User "1" --> "*" LifecycleEvent : creates
    EventLedger "1" --> "*" LifecycleEvent : manages
    ChainVerifier ..> LifecycleEvent : verifies

    class Product {
        <<external>>
        -uuid
        +get_uuid()
    }

    class User {
        <<external>>
        -email
        -role
        +get_email()
        +get_role()
    }

    class LifecycleEvent {
        -product_uuid
        -event_type
        -timestamp
        -actor_email
        -details
        -previous_hash
        -event_hash
        -sealed
        +__init__()
        +initialize()
        +calculate_hash()
        +get_product_uuid()
        +get_event_type()
        +get_timestamp()
        +get_actor_email()
        +get_details()
        +get_previous_hash()
        +get_event_hash()
        +get_event_data()
        +set_product_uuid()
        +set_event_type()
        +set_actor_email()
        +set_details()
        +set_previous_hash()
    }

    class EventLedger {
        +GENESIS_HASH
        +EVENT_PERMISSIONS
        -genesis_hash
        -events
        -score_engine_callback
        +__init__()
        +initialize()
        +get_genesis_hash()
        +get_history()
        +get_events()
        +set_genesis_hash()
        +add_event()
    }

    class ChainVerifier {
        -genesis_hash
        -result
        +__init__()
        +initialize()
        +get_genesis_hash()
        +get_result()
        +set_genesis_hash()
        +verify_chain()
        +first_broken_event()
    }
```

### Subsystem 3: Circularity score engine
### Classes: ScoreCalculator, ScoreWeights, CircularityScore, Subscore and Grade

```mermaid
classDiagram
    class ScoreCalculator {
        -config
        -weights
        -grades
        -params
        +__init__(config)
        +from_config_file(path)
        +calculate(product)
        +recalculate_all(db_path, trigger, only_if_changed)
        +describe()
    }

    class ScoreWeights {
        +recycled_content
        +repairability
        +lifespan
        +recyclability
        +hazard_free
        +__post_init__()
        +from_dict(d)
        +as_dict()
    }

    class CircularityScore {
        +product_id
        +total
        +grade
        +sub_scores
        +incomplete
        +missing_fields
        +computed_at
        +calc_ms
        +grade_letter()
        +sub_score(name)
        +breakdown()
        +to_record(trigger)
    }

    class SubScore {
        +name
        +value
        +weight
        +label()
        +points()
    }

    class Grade {
        +letter
        +min_score
    }


    ScoreCalculator ..> ScoreWeights : uses
    ScoreCalculator ..> CircularityScore : creates
    CircularityScore "1" *-- "1..*" SubScore : contains
    CircularityScore ..> Grade : assigned grade
    
```



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
