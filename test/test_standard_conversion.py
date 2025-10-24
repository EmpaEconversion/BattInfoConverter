"""Test module for standard Excel to JSON-LD conversion."""
import copy
import io
import json
from decimal import Decimal
from pathlib import Path

from battinfoconverter_backend.json_convert import convert_excel_to_jsonld

FIXTURE_DIR = Path(__file__).resolve().parent

IGNORED_COMMENT_PREFIXES = (
    "BattINFO Converter version:",
    "Software credit:",
    "BattINFO CoinCellSchema version:",
)

STANDARD_EXCEL_PATH = FIXTURE_DIR / "version1.1.10.xlsx"
STANDARD_JSON_PATH = FIXTURE_DIR / "BattINFO_converter_version1.1.10.json"


def _coerce_decimals(value):
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
    normalized.pop("schema:version", None)

    comments = normalized.get("rdfs:comment")
    if isinstance(comments, list):
        filtered_comments = [
            comment
            for comment in comments
            if not comment.startswith(IGNORED_COMMENT_PREFIXES)
        ]
        if filtered_comments:
            normalized["rdfs:comment"] = filtered_comments
        else:
            normalized.pop("rdfs:comment", None)

    return normalized


def test_standard_excel_conversion_matches_reference_jsonld():
    """Validate the Excel fixture converts to the canonical JSON-LD output."""

    converted = convert_excel_to_jsonld(STANDARD_EXCEL_PATH, debug_mode=False)
    with STANDARD_JSON_PATH.open(encoding="utf-8") as json_file:
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
