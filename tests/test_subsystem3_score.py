"""15 pytest tests for Subsystem 3.  Run from the project folder:  python -m pytest tests/test_subsystem3_score.py -v"""
import logging
import sqlite3
from types import SimpleNamespace

import pytest

from subsystem3_score import score_repository
from subsystem3_score.errors import ProductNotFoundError, ScoreErrorHandler
from subsystem3_score.score_calculator import ScoreCalculator
from subsystem3_score.score_service import ScoreService

PRODUCT = {"product_id": "TEST-001", "category": "Laptop", "expected_lifetime_years": 9,
           "spare_parts_percent": 50, "repair_count": 1}
MATERIALS = [{"material": "Aluminium", "percent": 60, "recycled": 40, "recyclable": True, "hazard": False},
             {"material": "Plastic", "percent": 30, "recycled": 10, "recyclable": True, "hazard": False},
             {"material": "Lithium battery", "percent": 10, "recycled": 0, "recyclable": True, "hazard": True}]


@pytest.fixture
def calculator():
    return ScoreCalculator()


@pytest.fixture
def db(tmp_path, monkeypatch):
    """A temporary SQLite database with one product, so no shared data is touched."""
    path = tmp_path / "test.db"
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE products (uuid TEXT, category TEXT, lifespan_years REAL, spare_parts_percent REAL);
        CREATE TABLE lifecycle_events (id INTEGER PRIMARY KEY, product_uuid TEXT, event_type TEXT);
        CREATE TABLE material_components (id INTEGER PRIMARY KEY, product_uuid TEXT, material TEXT,
            percent REAL, recycled INTEGER, recyclable INTEGER, hazard INTEGER);
        CREATE TABLE circularity_scores (id INTEGER PRIMARY KEY, product_uuid TEXT, total REAL, grade TEXT,
            sub_scores TEXT, missing TEXT, reason TEXT, computed_at TEXT);
        INSERT INTO products VALUES ('P1', 'Laptop', 9, 50);
        INSERT INTO material_components (product_uuid, material, percent, recycled, recyclable, hazard) VALUES
            ('P1', 'Aluminium', 60, 1, 1, 0), ('P1', 'Plastic', 30, 0, 1, 0), ('P1', 'Lithium battery', 10, 0, 1, 1);
    """)
    conn.commit()

    def connect():
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        return connection
    monkeypatch.setattr(score_repository, "connect", connect)
    yield conn
    conn.close()


def test_01_total_score_and_grade(calculator):
    score = calculator.calculate(PRODUCT, MATERIALS)
    values = {s.name: s.value for s in score.sub_scores}
    assert values == {"recycled_content": 27.0, "repairability": 50.0, "lifespan": 90.0,
                      "recyclability": 100.0, "hazard": 90.0}
    assert score.total == 69.9
    assert score.grade.letter == "B"
    assert not score.incomplete


def test_02_missing_data_is_reported_and_counts_as_zero(calculator):
    score = calculator.calculate({**PRODUCT, "spare_parts_percent": None}, MATERIALS)
    assert score.incomplete
    assert score.missing == ["Repairability"]
    assert score.total == 57.4


def test_03_unknown_product_raises_product_not_found(calculator):
    with pytest.raises(ProductNotFoundError):
        calculator.recalculate("UNKNOWN")
    event = SimpleNamespace(product_id="UNKNOWN", event_type="repaired", corrects_event_id=None)
    with pytest.raises(ProductNotFoundError):
        calculator.on_event(event)


def test_04_unexpected_errors_do_not_leak_details(caplog):
    handler = ScoreErrorHandler()
    with caplog.at_level(logging.ERROR, logger="subsystem3"):
        response = handler.to_response(RuntimeError("secret database password"))
    assert response["status"] == 500
    assert "secret" not in response["message"]
    assert handler.to_response(ValueError("bad value"))["status"] == 400


def test_05_repair_event_raises_score_and_history_keeps_both(db):
    service = ScoreService()
    first = service.on_registered("P1")
    db.execute("INSERT INTO lifecycle_events (product_uuid, event_type) VALUES ('P1', 'repaired')")
    db.commit()
    event = SimpleNamespace(get_product_uuid=lambda: "P1", get_event_type=lambda: "repaired")
    second = service.on_event(event)
    assert second.total > first.total
    history = service.history("P1")
    assert [h["reason"] for h in history] == ["registered", "event: repaired"]
    assert [h["total"] for h in history] == [first.total, second.total]


# ---------------------------------------------------------------------------
# Helpers and additional tests (06-15)
# ---------------------------------------------------------------------------
def _values(score):
    return {s.name: s.value for s in score.sub_scores}


def test_06_total_is_between_0_and_100(calculator):
    score = calculator.calculate(PRODUCT, MATERIALS)
    assert 0 <= score.total <= 100
    assert all(0 <= s.value <= 100 for s in score.sub_scores)


def test_07_fully_recycled_materials_give_full_recycled_content(calculator):
    recycled = [{**m, "recycled": 100} for m in MATERIALS]
    score = calculator.calculate(PRODUCT, recycled)
    assert _values(score)["recycled_content"] == 100.0
    assert score.total > 69.9


def test_08_no_recycled_content_scores_zero(calculator):
    virgin = [{**m, "recycled": 0} for m in MATERIALS]
    score = calculator.calculate(PRODUCT, virgin)
    assert _values(score)["recycled_content"] == 0.0
    assert score.total < 69.9


def test_09_removing_hazardous_material_improves_hazard_score(calculator):
    safe = [{**m, "hazard": False} for m in MATERIALS]
    baseline = calculator.calculate(PRODUCT, MATERIALS)
    improved = calculator.calculate(PRODUCT, safe)
    assert _values(improved)["hazard"] > _values(baseline)["hazard"]
    assert improved.total > baseline.total


def test_10_longer_expected_lifetime_improves_lifespan_score(calculator):
    short = calculator.calculate({**PRODUCT, "expected_lifetime_years": 3}, MATERIALS)
    long_ = calculator.calculate({**PRODUCT, "expected_lifetime_years": 9}, MATERIALS)
    assert _values(long_)["lifespan"] > _values(short)["lifespan"]
    assert long_.total > short.total


def test_11_more_spare_parts_improves_repairability(calculator):
    low = calculator.calculate({**PRODUCT, "spare_parts_percent": 20}, MATERIALS)
    high = calculator.calculate({**PRODUCT, "spare_parts_percent": 80}, MATERIALS)
    assert _values(high)["repairability"] > _values(low)["repairability"]
    assert high.total > low.total


def test_12_missing_lifespan_is_reported_and_lowers_total(calculator):
    baseline = calculator.calculate(PRODUCT, MATERIALS)
    score = calculator.calculate({**PRODUCT, "expected_lifetime_years": None}, MATERIALS)
    assert score.incomplete
    assert "Lifespan" in score.missing
    assert score.total < baseline.total


def test_13_calculation_is_deterministic_and_does_not_modify_input(calculator):
    product_before = dict(PRODUCT)
    materials_before = [dict(m) for m in MATERIALS]
    first = calculator.calculate(PRODUCT, MATERIALS)
    second = calculator.calculate(PRODUCT, MATERIALS)
    assert first.total == second.total
    assert _values(first) == _values(second)
    assert PRODUCT == product_before
    assert MATERIALS == materials_before


def test_14_product_not_found_maps_to_a_client_error_status():
    handler = ScoreErrorHandler()
    response = handler.to_response(ProductNotFoundError("UNKNOWN"))
    assert 400 <= response["status"] < 500
    assert response["message"]


def test_15_registering_a_product_stores_one_score_row(db):
    service = ScoreService()
    score = service.on_registered("P1")
    rows = db.execute("SELECT total, reason FROM circularity_scores WHERE product_uuid = 'P1'").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == score.total
    assert rows[0][1] == "registered"
