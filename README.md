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

## Run it

Tested with Python 3.14. Run every command from this folder.

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

To read the description of each subsystem's classes, with their methods, getters and setters (press `q` to close it):

```bash
python -m pydoc subsystem1_passport
python -m pydoc subsystem2_ledger
python -m pydoc subsystem3_score
python -m pydoc subsystem4_ai_engine
```

Each folder's `__init__.py` lists its classes, which is why these commands can show them.

Each subsystem has a demo that creates its objects, uses their getters and setters, and prints the results:

```bash
python -m subsystem1_passport.demo
python -m subsystem2_ledger.demo
python -m subsystem3_score.demo
python -m subsystem4_ai_engine.demo
```

The demos need no API key and no extra setup. Each subsystem runs on its own.

### Optional: the real AI

The Subsystem 4 demo uses the rule-based advisor and does not load the CLIP image model. To identify a real photo with CLIP, install its large packages and give the demo a photo. The first run also downloads the model.

```bash
pip install -r requirements-clip.txt
python -m subsystem4_ai_engine.demo path/to/photo.jpg
```

To use the LLM, set an API key from https://chat.kiconnect.nrw as an environment variable. The key is never stored in the code.

```bash
export KICONNECT_API_KEY="your-key"
```

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

### Classes: `EventLedger`, `LifecycleEvent`, `EventHasher`, `ChainVerifier`

```mermaid
classDiagram

    class EventLedger {
        -_events: dict
        -_genesis_hash: str
        -_score_engine_callback
        -_event_hasher: EventHasher
        +add_event(product, actor, event_type, details)
        +get_history(product_uuid)
        +get_events()
        +get_genesis_hash()
    }

    class LifecycleEvent {
        -_product_uuid
        -_event_type
        -_timestamp
        -_actor_email
        -_details
        -_previous_hash
        -_event_hash
        +get_event_data()
        +get_event_hash()
        +get_previous_hash()
    }

    class EventHasher {
        -_algorithm: str
        +calculate_hash(event)
        +verify_hash(event)
    }

    class ChainVerifier {
        -_genesis_hash: str
        -_result: dict
        -_event_hasher: EventHasher
        +verify_chain(events)
        +first_broken_event()
        +get_result()
    }

    EventLedger "1" --> "0..*" LifecycleEvent : manages
    EventLedger "1" --> "1" EventHasher : uses
    ChainVerifier "1" --> "1" EventHasher : uses
    ChainVerifier "1" ..> "0..*" LifecycleEvent : verifies
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
    ImageClassifier ..> AIPrediction : creates
    Recommender ..> AIPrediction : creates
    Recommender "1" --> "0..1" LLMAdapter : asks first
    Recommender "1" --> "1" RuleBasedAdvisor : falls back to
    class ImageClassifier {
        +model_name : get/set
        +revision : get/set
        +uncertain_below : get/set
        +top_k : get/set
        +is_loaded : get only
        +initialize()
        +classify(photo)
    }
    class AIPrediction {
        +kind : get/set
        +result : get/set
        +model_name : get/set
        +version : get/set
        +product_id : get/set
        +rating : get/set
        +created_at : get only
        +initialize()
        +to_dict()
        +save(path)
        +latest(kind, product_id, path)
    }
    class Recommender {
        +adapter : get/set
        +advisor : get/set
        +timeout : get/set
        +reason : get only
        +initialize(adapter, advisor)
        +recommend(product, circularity_score)
    }
    class RuleBasedAdvisor {
        +resale_reusability : get/set
        +reuse_reusability : get/set
        +repair_repairability : get/set
        +min_resale_years : get/set
        +current_year : get/set
        +initialize(current_year)
        +advise(product)
    }
    class LLMAdapter {
        +provider : get/set
        +model : get/set
        +max_tokens : get/set
        +base_url : get only
        +has_api_key : get only
        +last_model : get only
        +last_version : get only
        +last_finish_reason : get only
        +initialize()
        +complete(prompt, system, history, timeout)
    }
```
