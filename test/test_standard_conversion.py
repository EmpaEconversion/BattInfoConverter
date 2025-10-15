import copy
import json
from pathlib import Path

from battinfoconverter_backend.json_convert import convert_excel_to_jsonld

FIXTURE_DIR = Path(__file__).resolve().parent

IGNORED_COMMENT_PREFIXES = (
    "BattINFO Converter version:",
    "Software credit:",
    "BattINFO CoinCellSchema version:",
)


def _normalize_jsonld(payload: dict) -> dict:
    normalized = copy.deepcopy(payload)
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
    excel_path = FIXTURE_DIR / "Standard_Excel.xlsx"
    expected_json_path = FIXTURE_DIR / "Standard_JSON.json"

    converted = convert_excel_to_jsonld(str(excel_path), debug_mode=False)
    with expected_json_path.open(encoding="utf-8") as json_file:
        expected = json.load(json_file)

    assert _normalize_jsonld(converted) == _normalize_jsonld(expected)
