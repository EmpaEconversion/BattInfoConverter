"""Test module for standard Excel to JSON-LD conversion."""

import copy
import io
import json
from decimal import Decimal
from pathlib import Path

import pytest
from pyld import jsonld

from battinfoconverter_backend.json_convert import convert_excel_to_jsonld
from battinfoconverter_backend.validate import validate_jsonld

FIXTURE_DIR = Path(__file__).resolve().parent

IGNORED_COMMENT_PREFIXES = (
    "BattINFO Converter version:",
    "Software credit:",
    "BattINFO CoinCellSchema version:",
    "Schema version:",
)

STANDARD_EXCEL_PATH = FIXTURE_DIR / "BattINFO_converter_standard_Excel_version_1.1.17.xlsx"
STANDARD_JSON_PATH = FIXTURE_DIR / "BattINFO_converter_BattINFO_converter_standard_JSON_version_1.1.17.json"

STANDARD_CATALYSIS_EXCEL_PATH = FIXTURE_DIR / "standard_catalysis_excel_schema.xlsx"
STANDARD_CATALYSIS_JSON_PATH = FIXTURE_DIR / "standard_catalysis_json_schema.json"

jsonld.set_document_loader(jsonld.requests_document_loader())


def _coerce_decimals(value: Decimal | float | dict | list) -> float | dict | list:
    """Recursively convert ``Decimal`` instances within ``value`` to floats."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: _coerce_decimals(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_coerce_decimals(item) for item in value]
    return value


def _normalize_jsonld(payload: dict) -> dict:
    """Return a copy of ``payload`` with version metadata removed for comparison."""
    normalized = _coerce_decimals(copy.deepcopy(payload))
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



def test_standard_battinfo() -> None:
    """Check that coin cell Excel conversion matches expected JSON-LD output."""
    converted = convert_excel_to_jsonld(STANDARD_EXCEL_PATH, debug_mode=False)
    with STANDARD_JSON_PATH.open(encoding="utf-8") as json_file:
        expected = json.load(json_file)

    assert _normalize_jsonld(converted) == _normalize_jsonld(expected)


def test_standard_catinfo() -> None:
    """Check that catalysis Excel conversion matches expected JSON-LD output."""
    converted = convert_excel_to_jsonld(STANDARD_CATALYSIS_EXCEL_PATH, debug_mode=False)
    with STANDARD_CATALYSIS_JSON_PATH.open(encoding="utf-8") as json_file:
        expected = json.load(json_file)

    assert _normalize_jsonld(converted) == _normalize_jsonld(expected)


def test_valid_json() -> None:
    """Make sure the JSON-LD output is valid."""
    converted = convert_excel_to_jsonld(STANDARD_EXCEL_PATH, debug_mode=False)
    # This should run without errors
    json.dumps(converted)


def test_conversion_different_inputs() -> None:
    """Users should be able to read files in different ways."""
    # pathlib.Path object
    res1 = convert_excel_to_jsonld(STANDARD_EXCEL_PATH, debug_mode=False)

    # String object
    res2 = convert_excel_to_jsonld(str(STANDARD_EXCEL_PATH), debug_mode=False)

    # Buffered reader object
    with STANDARD_EXCEL_PATH.open("rb") as f:
        excel_bytesio = io.BytesIO(f.read())
        res3 = convert_excel_to_jsonld(f, debug_mode=False)

    # Bytes IO object
    res4 = convert_excel_to_jsonld(excel_bytesio, debug_mode=False)

    # Should not affect the results
    assert res1 == res2 == res3 == res4


def test_valid_jsonld() -> None:
    """Check that the JSON-LD output canonizes without error."""
    converted = convert_excel_to_jsonld(STANDARD_EXCEL_PATH, debug_mode=False)
    # This should run without errors
    jsonld.normalize(converted, {"algorithm": "URDNA2015", "format": "application/n-quads"})
    jsonld.expand(converted)


def test_against_cached_context() -> None:
    """Make sure all terms are mapped in the cached context."""
    # The standard filled excel template must pass
    converted = convert_excel_to_jsonld(STANDARD_EXCEL_PATH)
    validate_jsonld(converted, errors="raise")

    # Validation should not modify original dict
    assert converted == convert_excel_to_jsonld(STANDARD_EXCEL_PATH)

    # Sanity check - these should all fail
    bad_jsonld = converted.copy()
    bad_jsonld["hasSomethingNotAllowed"] = {"@id": "CoinCell"}
    with pytest.raises(ValueError, match="'hasSomethingNotAllowed' was not found"):
        validate_jsonld(bad_jsonld, errors="raise")

    bad_jsonld = converted.copy()
    bad_jsonld["hasComponent"] = {"@id": "ThisDoesNotExist"}
    with pytest.raises(ValueError, match="'ThisDoesNotExist' was not found"):
        validate_jsonld(bad_jsonld, errors="raise")

    bad_jsonld = converted.copy()
    bad_jsonld["hasComponent"] = {"@type": ["CoinCell", "ThisDoesNotExist"]}
    with pytest.raises(ValueError, match="'ThisDoesNotExist' was not found"):
        validate_jsonld(bad_jsonld, errors="raise")

    # This is currently allowed - string literal with no IRI
    bad_jsonld = converted.copy()
    bad_jsonld["hasComponent"] = "ThisDoesNotExist"
    validate_jsonld(bad_jsonld, errors="raise")
