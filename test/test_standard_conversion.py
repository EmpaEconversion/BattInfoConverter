"""Test module for standard Excel to JSON-LD conversion."""

import copy
import io
import json
import re
from decimal import Decimal
from pathlib import Path

from pyld import jsonld
from pyld.jsonld import JsonLdProcessor

from battinfoconverter_backend.json_convert import convert_excel_to_jsonld

FIXTURE_DIR = Path(__file__).resolve().parent

IGNORED_COMMENT_PREFIXES = (
    "BattINFO Converter version:",
    "Software credit:",
    "BattINFO CoinCellSchema version:",
    "Schema version:",
)

STANDARD_EXCEL_PATH = FIXTURE_DIR / "BattINFO_converter_standard_Excel_version_1.1.16.xlsx"
STANDARD_JSON_PATH = FIXTURE_DIR / "BattINFO_converter_BattINFO_converter_standard_JSON_version_1.1.16.json"

STANDARD_CATALYSIS_EXCEL_PATH = FIXTURE_DIR / "standard_catalysis_excel_schema.xlsx"
STANDARD_CATALYSIS_JSON_PATH = FIXTURE_DIR / "standard_catalysis_json_schema.json"


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


def _find_dropped_terms(doc: dict) -> list[str]:
    """Find any terms that do not resolve to aboslute IRIs.

    This does not check values.
    """
    # Use pyld to process the context and fetch remotes
    processor = JsonLdProcessor()
    active_ctx = processor.process_context(processor._get_initial_context({}), doc["@context"], {})

    # active_ctx["mappings"] is a dict of term -> {"@id": "<absolute IRI>", ...}
    mapped_terms = set(active_ctx.get("mappings", {}).keys())

    # Collect compact term names used as keys in the raw doc
    def raw_term_keys(obj: list | dict | str | float, seen: set | None = None) -> set:
        """Recursive search for all terms."""
        if seen is None:
            seen = set()
        if isinstance(obj, dict):
            for k, v in obj.items():
                if not k.startswith("@") and not re.match(r"^[A-Za-z][A-Za-z0-9+\-.]*:", k):
                    seen.add(k)
                raw_term_keys(v, seen)
        elif isinstance(obj, list):
            for i in obj:
                raw_term_keys(i, seen)
        return seen

    # Get all the terms in the json-ld
    raw_terms = raw_term_keys(doc)

    # Anything not in mapped_terms was not resolved by any context
    return [t for t in raw_terms if t not in mapped_terms]


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


def test_no_dropped_terms():
    """Check there are no unmapped terms in the JSON-LD."""
    converted = convert_excel_to_jsonld(STANDARD_EXCEL_PATH, debug_mode=False)
    dropped = _find_dropped_terms(converted)
    assert not dropped, (
        f"{len(dropped)} term(s) were silently dropped during expansion "
        f"(not in any context, including the remote base):\n" + "\n".join(f"  {t!r}" for t in sorted(dropped))
    )

    # Sanity check, it should fail with missing terms
    converted["hasSomethingThatDoesntExist"] = converted.pop("hasCase")
    dropped = _find_dropped_terms(converted)
    assert dropped == ["hasSomethingThatDoesntExist"]
