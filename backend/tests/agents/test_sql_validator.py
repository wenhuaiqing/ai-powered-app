"""Tier-1 tests for the DuckDB sql_validator."""

from __future__ import annotations

import pytest

from src.app.services.sql_validator import (
    ALLOWED_TABLES,
    DEFAULT_LIMIT,
    MAX_LIMIT,
    validate,
)


def test_select_passes_and_injects_limit():
    outcome = validate("SELECT suburb, AVG(price) FROM properties GROUP BY suburb")
    assert outcome.ok
    assert f"LIMIT {DEFAULT_LIMIT}" in outcome.sql.upper()
    assert "properties" in outcome.tables_referenced


def test_existing_limit_is_kept():
    outcome = validate("SELECT * FROM properties LIMIT 25")
    assert outcome.ok
    assert "LIMIT 25" in outcome.sql.upper()


def test_excessive_limit_is_clamped():
    outcome = validate(f"SELECT * FROM properties LIMIT {MAX_LIMIT + 1000}")
    assert outcome.ok
    assert f"LIMIT {MAX_LIMIT}" in outcome.sql.upper()


def test_join_allowlist_passes():
    outcome = validate(
        "SELECT p.suburb, l.asking_price "
        "FROM listings l JOIN properties p ON l.property_id = p.property_id"
    )
    assert outcome.ok
    assert {"listings", "properties"}.issubset(set(outcome.tables_referenced))


@pytest.mark.parametrize(
    "sql, expected_error_contains",
    [
        ("DROP TABLE properties", "forbidden"),
        ("INSERT INTO properties VALUES (1)", "forbidden"),
        ("DELETE FROM listings", "forbidden"),
        ("UPDATE properties SET price = 0", "forbidden"),
        ("ATTACH 'evil.db' AS evil", "forbidden"),
        ("PRAGMA database_list", "forbidden"),
        ("SELECT * FROM users", "allowlist"),
        ("SELECT 1; DROP TABLE properties", "multiple statements"),
    ],
)
def test_dangerous_inputs_rejected(sql: str, expected_error_contains: str):
    outcome = validate(sql)
    assert not outcome.ok
    assert any(expected_error_contains in e for e in outcome.errors), outcome.errors


def test_empty_input_rejected():
    outcome = validate("")
    assert not outcome.ok
    assert outcome.errors


def test_comments_are_stripped_before_check():
    outcome = validate("-- nasty comment\nSELECT * FROM properties /* inline */ LIMIT 5")
    assert outcome.ok


def test_with_cte_allowed():
    outcome = validate(
        "WITH top_suburbs AS (SELECT suburb FROM properties GROUP BY suburb LIMIT 5) "
        "SELECT * FROM top_suburbs"
    )
    assert outcome.ok


def test_all_allowed_tables_recognised():
    for table in ALLOWED_TABLES:
        outcome = validate(f"SELECT * FROM {table}")
        assert outcome.ok, f"validator rejected allowlisted table {table}: {outcome.errors}"
