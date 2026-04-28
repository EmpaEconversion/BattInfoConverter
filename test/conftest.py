"""Pytest set up and helper functions."""

import copy
import json
from decimal import Decimal
from pathlib import Path

import pytest
from pyld import jsonld

jsonld.set_document_loader(jsonld.requests_document_loader())

IGNORED_COMMENT_PREFIXES = (
    "BattINFO Converter version:",
    "Software credit:",
    "BattINFO CoinCellSchema version:",
    "Schema version:",
)

FIXTURE_DIR = Path(__file__).resolve().parent

STANDARD_COINCELL_EXCEL_PATH = FIXTURE_DIR / "standard_coincell_excel_schema.xlsx"
STANDARD_COINCELL_JSON_PATH = FIXTURE_DIR / "standard_coincell_json_schema.json"

STANDARD_CATALYSIS_EXCEL_PATH = FIXTURE_DIR / "standard_catalysis_excel_schema.xlsx"
STANDARD_CATALYSIS_JSON_PATH = FIXTURE_DIR / "standard_catalysis_json_schema.json"


@pytest.fixture
def coincell_excel_path() -> Path:
    """Path to standard coin cell excel."""
    return STANDARD_COINCELL_EXCEL_PATH


@pytest.fixture
def coincell_jsonld() -> dict:
    """Get dict of expected json-ld output."""
    with STANDARD_COINCELL_JSON_PATH.open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def catalysis_excel_path() -> Path:
    """Path to standard catalysis excel."""
    return STANDARD_CATALYSIS_EXCEL_PATH


@pytest.fixture
def catalysis_jsonld() -> dict:
    """Get dict of expected json-ld output."""
    with STANDARD_CATALYSIS_JSON_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def coerce_decimals(value: Decimal | float | dict | list) -> float | dict | list:
    """Recursively convert ``Decimal`` instances within ``value`` to floats."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: coerce_decimals(item) for key, item in value.items()}
    if isinstance(value, list):
        return [coerce_decimals(item) for item in value]
    return value


def normalize_jsonld(payload: dict) -> dict:
    """Return a copy of ``payload`` with version metadata removed for comparison."""
    normalized = coerce_decimals(copy.deepcopy(payload))
    assert isinstance(normalized, dict)
    normalized.pop("schema:version", None)
    comments = normalized.get("rdfs:comment")
    if isinstance(comments, list):
        filtered_comments = [comment for comment in comments if not comment.startswith(IGNORED_COMMENT_PREFIXES)]
        if filtered_comments:
            normalized["rdfs:comment"] = filtered_comments
        else:
            normalized.pop("rdfs:comment", None)
    return normalized
