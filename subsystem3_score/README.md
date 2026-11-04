# Subsystem 3 – Circularity Score 

Each of the five classes is in its own Python module. Every class provides:

1. A constructor (`__init__`) that initializes its state.
2. An `initialize()` method for setup and validation.
3. Getter and setter methods (and Python properties where appropriate) for its attributes.



## Classes

| Class | Module | Main responsibility |
|---|---|---|
| `ScoreWeights` | `score_weights.py` | Initializes and validates the five weights; offers getters and an atomic `set_weights()` method. |
| `Grade` | `grade.py` | Stores a grade letter and minimum score threshold. |
| `SubScore` | `sub_score.py` | Stores one sub-score name, value and weight. |
| `CircularityScore` | `circularity_score.py` | Stores the complete calculated result, breakdown, missing fields and timestamp. |
| `ScoreCalculator` | `score_calculator.py` | Loads configuration, initializes scoring parameters and calculates product scores. |

The five independent calculation functions remain in `scoring_functions.py` and are called by `ScoreCalculator`.

### Requirements
- Python 3.10 or later

## Run the demonstration

From this folder, run:

```bash
python -m subsystem3_score.demo
```

This initializes all five classes, demonstrates getters/setters, loads `score_config.json`, and calculates a sample product score.



`score_config.json` contains editable scoring weights, grade thresholds and formula parameters. The calculator validates the configuration when initialized or reloaded.
