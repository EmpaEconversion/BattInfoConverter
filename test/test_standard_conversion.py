"""Test module for standard Excel to JSON-LD conversion."""
import copy
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
    excel_path = FIXTURE_DIR / "adjust_251006_250515_241125_Battery2030+_CoinCellBattery_Schema_Ontologized_1.1.8_filled.xlsx"
    expected_json_path = FIXTURE_DIR / "adjust_BattINFO_converter_adjust_251006_250515_241125_Battery2030+_CoinCellBattery_Schema_Ontologized_1.1.8_filled.json"

    converted = convert_excel_to_jsonld(excel_path, debug_mode=False)
    with expected_json_path.open(encoding="utf-8") as json_file:
        expected = json.load(json_file)

    assert _normalize_jsonld(converted) == _normalize_jsonld(expected)

def test_valid_json() -> None:
    """Make sure the JSON-LD output is valid."""
    excel_path = FIXTURE_DIR / "adjust_251006_250515_241125_Battery2030+_CoinCellBattery_Schema_Ontologized_1.1.8_filled.xlsx"
    converted = convert_excel_to_jsonld(excel_path, debug_mode=False)
    # This should run without errors
    json.dumps(converted)
