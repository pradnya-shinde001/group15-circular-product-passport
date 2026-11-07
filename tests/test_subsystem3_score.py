"""5 pytest tests for Subsystem 3.  Run from the project folder:  python -m pytest tests/test_subsystem3_score.py -v"""
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
