"""Circularity Score Engine (Subsystem 3).

Classes (see class diagram):  ScoreCalculator, ScoreWeights, CircularityScore, SubScore, Grade and configError.

Formula (scoring parameters are defined directly in Python):

    total = w1*RecycledContent + w2*Repairability + w3*Lifespan
          + w4*Recyclability   + w5*HazardFree                (each sub-score is 0-100)

  RecycledContent = recycled% / target% * 100                          (capped at 100)
  Repairability   = design_share*design + parts_share*spare_parts - penalty_per_repair*repairs
  Lifespan        = expected_years / category_average / full_score_ratio * 100   (capped at 100)
  Recyclability   = recyclable share of the product in %
  HazardFree      = 100 - penalty_per_substance * number_of_hazardous_substances  (the hazardous-material penalty)

Every sub-score is its own pure function (testable alone), is rounded to ONE decimal
(half-up) and the total is calculated from those rounded sub-scores, so the numbers
shown on screen add up. No randomness anywhere: same input -> same score.
Missing data never raises an error: the score is flagged `incomplete` and the total is
provisional (weights of the available sub-scores are re-normalised).
"""
import math
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple

import score_store

SUB_SCORE_KEYS = ("recycled_content", "repairability", "lifespan", "recyclability", "hazard_free")
LABELS = {
    "recycled_content": "Recycled content",
    "repairability": "Repairability",
    "lifespan": "Lifespan",
    "recyclability": "Recyclability",
    "hazard_free": "Hazard-free",
}
# Which product fields each sub-score needs (used for the "incomplete" flag)
REQUIRED_FIELDS = {
    "recycled_content": ("recycled_material_percent",),
    "repairability": ("repairability_score", "spare_parts_availability", "repair_count"),
    "lifespan": ("expected_lifetime_years",),
    "recyclability": ("recyclability_score",),
    "hazard_free": ("hazardous_materials_count",),
}
WEIGHT_TOLERANCE = 1e-6


class ConfigError(ValueError):
    """The score configuration is invalid (e.g. weights do not sum to 1.0)."""


# ------------------------------------------------------------------ helpers
def round1(x):
    """Round to one decimal, half-up (hand calculation style): 75.25 -> 75.3."""
    if x is None:
        return None
    return float(Decimal(str(round(x, 6))).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def to_number(value):
    """float(value), or None when the value is missing / not numeric / NaN."""
    if value is None:
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) or math.isinf(x) else x


def clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))


# --------------------------------------------- the five sub-score functions
# Each one is pure, takes plain numbers, returns a value 0-100 (1 decimal) or None.
def recycled_content_score(recycled_percent, target_percent=70.0):
    if recycled_percent is None:
        return None
    return round1(clamp(recycled_percent / target_percent * 100))


def repairability_score(design_score, parts_availability, repair_count,
                        design_share=0.7, parts_share=0.3, penalty_per_repair=3.0):
    if design_score is None or parts_availability is None or repair_count is None:
        return None
    value = design_share * design_score + parts_share * parts_availability \
        - penalty_per_repair * max(repair_count, 0)
    return round1(clamp(value))


def lifespan_score(expected_years, category, category_averages, full_score_ratio=1.5):
    """Expected lifetime compared with the average of the product's category."""
    if expected_years is None:
        return None
    average = category_averages.get(category, category_averages["default"])
    return round1(clamp(expected_years / average / full_score_ratio * 100))


def recyclability_score(recyclable_share):
    if recyclable_share is None:
        return None
    return round1(clamp(recyclable_share))


def hazard_free_score(hazard_count, penalty_per_substance=25.0):
    """100 minus the hazardous-material penalty."""
    if hazard_count is None:
        return None
    return round1(clamp(100 - penalty_per_substance * max(hazard_count, 0)))


# ------------------------------------------------------------------ classes
@dataclass(frozen=True)
class ScoreWeights:
    """Five weights. Must sum to 1.0 (NFR 5)."""
    recycled_content: float
    repairability: float
    lifespan: float
    recyclability: float
    hazard_free: float

    def __post_init__(self):
        for key in SUB_SCORE_KEYS:
            v = getattr(self, key)
            if not isinstance(v, (int, float)) or isinstance(v, bool) or not 0 <= v <= 1:
                raise ConfigError(f"Weight '{key}' must be a number between 0 and 1 (got {v!r}).")
        total = sum(getattr(self, k) for k in SUB_SCORE_KEYS)
        if abs(total - 1.0) > WEIGHT_TOLERANCE:
            raise ConfigError(f"Weights must sum to 1.0, but they sum to {total:.6g}.")

    @classmethod
    def from_dict(cls, d):
        if set(d) != set(SUB_SCORE_KEYS):
            raise ConfigError(f"Weights must be exactly: {', '.join(SUB_SCORE_KEYS)}.")
        return cls(**{k: d[k] for k in SUB_SCORE_KEYS})

    def as_dict(self):
        return {k: getattr(self, k) for k in SUB_SCORE_KEYS}


@dataclass(frozen=True)
class Grade:
    """A grade letter and the minimum total score needed for it."""
    letter: str
    min_score: float


def grade_for(total, grades):
    """grades: list of Grade sorted from best to worst."""
    if total is None:
        return None
    for g in grades:
        if total >= g.min_score:
            return g
    return grades[-1]


@dataclass(frozen=True)
class SubScore:
    name: str
    value: Optional[float]      # None = could not be calculated (missing data)
    weight: float

    @property
    def label(self):
        return LABELS[self.name]

    @property
    def points(self):
        """Contribution to the total (value * weight)."""
        return None if self.value is None else round1(self.value * self.weight)


@dataclass(frozen=True)
class CircularityScore:
    product_id: Optional[str]
    total: Optional[float]                 # 0-100, 1 decimal; None if nothing could be calculated
    grade: Optional[Grade]
    sub_scores: Tuple[SubScore, ...]
    incomplete: bool
    missing_fields: Tuple[str, ...]
    computed_at: str = field(compare=False, default="")
    calc_ms: float = field(compare=False, default=0.0)

    @property
    def grade_letter(self):
        return self.grade.letter if self.grade else None

    def sub_score(self, name):
        return next(s for s in self.sub_scores if s.name == name)

    def breakdown(self):
        return {s.name: s.value for s in self.sub_scores}

    def to_record(self, trigger="manual"):
        """Return a flat database record; no text serialization is used."""
        record = {
            "product_id": self.product_id, "total": self.total, "grade": self.grade_letter,
            "incomplete": int(self.incomplete), "trigger_event": trigger,
            "computed_at": self.computed_at, "missing_fields": ";".join(self.missing_fields),
        }
        for sub in self.sub_scores:
            record[f"{sub.name}_value"] = sub.value
            record[f"{sub.name}_weight"] = sub.weight
        return record



def _get(product, key):
    try:
        return product.get(key)           # dict, pandas Series
    except AttributeError:
        try:
            return product[key]           # sqlite3.Row
        except (IndexError, KeyError):
            return None


def default_config():
    """Built-in scoring rules. Edit these Python constants to change the model."""
    return {
        "weights": {"recycled_content": 0.20, "repairability": 0.25, "lifespan": 0.20,
                    "recyclability": 0.25, "hazard_free": 0.10},
        "grades": {"A": 80, "B": 65, "C": 50, "D": 35, "E": 0},
        "recycled_content": {"target_percent": 70},
        "repairability": {"design_share": 0.7, "parts_share": 0.3, "penalty_per_repair": 3},
        "lifespan": {"full_score_ratio": 1.5, "category_average_years":
                     {"Laptop": 5, "Smartphone": 3, "Monitor": 6, "Tablet": 4, "Other": 5, "default": 5}},
        "hazard": {"penalty_per_substance": 25},
    }


def parse_config(cfg):
    """Validate built-in or supplied Python configuration."""
    try:
        weights = ScoreWeights.from_dict(cfg["weights"])
        grades = sorted((Grade(k, float(v)) for k, v in cfg["grades"].items()),
                        key=lambda g: g.min_score, reverse=True)
        if len(grades) != 5 or [g.letter for g in grades] != ["A", "B", "C", "D", "E"]:
            raise ConfigError("Grades must be A, B, C, D, E with descending minimum scores.")
        params = {
            "recycled_target": float(cfg["recycled_content"]["target_percent"]),
            "design_share": float(cfg["repairability"]["design_share"]),
            "parts_share": float(cfg["repairability"]["parts_share"]),
            "penalty_per_repair": float(cfg["repairability"]["penalty_per_repair"]),
            "full_ratio": float(cfg["lifespan"]["full_score_ratio"]),
            "category_averages": {k: float(v) for k, v in cfg["lifespan"]["category_average_years"].items()},
            "penalty_per_substance": float(cfg["hazard"]["penalty_per_substance"]),
        }
    except ConfigError:
        raise
    except (KeyError, TypeError, ValueError, AttributeError) as e:
        raise ConfigError(f"Invalid built-in scoring configuration: {e!r}") from e
    if "default" not in params["category_averages"]:
        raise ConfigError("category_average_years needs a 'default' entry.")
    if params["recycled_target"] <= 0 or params["full_ratio"] <= 0 or any(v <= 0 for v in params["category_averages"].values()):
        raise ConfigError("Targets, ratios and category averages must be greater than 0.")
    return weights, grades, params


class ScoreCalculator:
    """calculate(product) and recalculate_all()."""

    def __init__(self, config):
        self.config = config
        self.weights, self.grades, self.params = parse_config(config)

    @classmethod
    def with_defaults(cls):
        return cls(default_config())

    # ---- FR 1-6, 9, 10 ----------------------------------------------------
    def calculate(self, product):
        """Score one product (dict / pandas row / sqlite3.Row). Never raises on missing data."""
        t0 = time.perf_counter()
        p = self.params
        g = lambda key: to_number(_get(product, key))

        values = {
            "recycled_content": recycled_content_score(g("recycled_material_percent"), p["recycled_target"]),
            "repairability": repairability_score(
                g("repairability_score"), g("spare_parts_availability"), g("repair_count"),
                p["design_share"], p["parts_share"], p["penalty_per_repair"]),
            "lifespan": lifespan_score(g("expected_lifetime_years"), _get(product, "category"),
                                       p["category_averages"], p["full_ratio"]),
            "recyclability": recyclability_score(g("recyclability_score")),
            "hazard_free": hazard_free_score(g("hazardous_materials_count"), p["penalty_per_substance"]),
        }
        w = self.weights.as_dict()
        subs = tuple(SubScore(k, values[k], w[k]) for k in SUB_SCORE_KEYS)

        missing = tuple(f for k in SUB_SCORE_KEYS for f in REQUIRED_FIELDS[k]
                        if to_number(_get(product, f)) is None)
        available = [s for s in subs if s.value is not None]
        incomplete = len(available) < len(subs)

        if not available:
            total = None
        else:
            weighted = sum(s.weight * s.value for s in available)
            total = round1(weighted / sum(s.weight for s in available) if incomplete else weighted)

        return CircularityScore(
            product_id=_get(product, "product_id"), total=total, grade=grade_for(total, self.grades),
            sub_scores=subs, incomplete=incomplete, missing_fields=missing,
            computed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            calc_ms=(time.perf_counter() - t0) * 1000,
        )

    # ---- FR 7 / NFR 10 ----------------------------------------------------
    def recalculate_all(self, db_path=score_store.DEFAULT_DB, trigger="batch", only_if_changed=False):
        """Recalculate every product and store the results in ONE transaction.
        With only_if_changed=True, products whose stored latest score is identical are skipped.
        Returns the number of stored scores."""
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            score_store.ensure_table(conn)
            latest = score_store.latest_by_product(conn) if only_if_changed else {}
            records = []
            for row in conn.execute("SELECT * FROM products"):
                s = self.calculate(row)
                rec = s.to_record(trigger)
                old = latest.get(s.product_id)
                current_parts = tuple((rec[f"{name}_value"], rec[f"{name}_weight"]) for name in SUB_SCORE_KEYS)
                if old and old["total"] == rec["total"] and old["sub_scores"] == current_parts:
                    continue
                records.append(rec)
            score_store.save_records(conn, records)
            conn.commit()
            return len(records)
        finally:
            conn.close()

    def describe(self):
        """Human-readable formula and weights (NFR 3)."""
        w, p = self.weights, self.params
        lines = [
            "**Total score** = " + " + ".join(f"{getattr(w, k):g} × {LABELS[k]}" for k in SUB_SCORE_KEYS),
            "",
            f"- **Recycled content** = recycled % ÷ {p['recycled_target']:g} % × 100 (max 100)",
            f"- **Repairability** = {p['design_share']:g} × design repairability + {p['parts_share']:g} × spare-parts "
            f"availability − {p['penalty_per_repair']:g} per previous repair",
            f"- **Lifespan** = expected years ÷ category average ÷ {p['full_ratio']:g} × 100 (max 100)",
            "- **Recyclability** = recyclable share of the product in %",
            f"- **Hazard-free** = 100 − {p['penalty_per_substance']:g} per hazardous substance (hazardous-material penalty)",
            "",
            "Grades: " + ", ".join(f"{g.letter} ≥ {g.min_score:g}" for g in self.grades),
            "Category average lifetimes (years): " + ", ".join(
                f"{k} {v:g}" for k, v in p["category_averages"].items()),
        ]
        return "\n".join(lines)


# ----------------------------------------------- backwards-compatible helpers
def calculate_circularity(row):
    """Total score only (old API)."""
    return ScoreCalculator.with_defaults().calculate(row).total


def score_label(score):
    """Grade letter for a total (old API)."""
    g = grade_for(score, ScoreCalculator.with_defaults().grades)
    return g.letter if g else None
