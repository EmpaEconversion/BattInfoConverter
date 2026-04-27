"""Test module for standard Excel to JSON-LD conversion."""

import json
from pathlib import Path

import pytest
from conftest import normalize_jsonld

from battinfoconverter_backend.json_convert import convert_excel_to_jsonld
from battinfoconverter_backend.templates.template_conversion import (
    COINCELL_TEMPLATE_PATH,
    dict_to_workbook,
    workbook_to_dict,
)

FIXTURE_DIR = Path(__file__).resolve().parent

IGNORED_COMMENT_PREFIXES = (
    "BattINFO Converter version:",
    "Software credit:",
    "BattINFO CoinCellSchema version:",
    "Schema version:",
)

STANDARD_COINCELL_EXCEL_PATH = FIXTURE_DIR / "standard_coincell_excel_schema.xlsx"
STANDARD_COINCELL_JSON_PATH = FIXTURE_DIR / "standard_coincell_json_schema.json"

STANDARD_CATALYSIS_EXCEL_PATH = FIXTURE_DIR / "standard_catalysis_excel_schema.xlsx"
STANDARD_CATALYSIS_JSON_PATH = FIXTURE_DIR / "standard_catalysis_json_schema.json"


def test_round_trip() -> None:
    """Template should survive roundtrips to excel and JSON."""
    with COINCELL_TEMPLATE_PATH.open("r") as f:
        data1 = json.load(f)
    wb1 = dict_to_workbook(data1)
    data2 = workbook_to_dict(wb1)
    wb2 = dict_to_workbook(data2)
    data3 = workbook_to_dict(wb2)
    assert data1 == data2
    assert data2 == data3


def test_template_does_not_warn(caplog: pytest.LogCaptureFixture) -> None:
    """The template should compile without any warnings."""
    with COINCELL_TEMPLATE_PATH.open("r") as f:
        data = json.load(f)
    wb = dict_to_workbook(data)
    convert_excel_to_jsonld(wb)
    assert caplog.text == ""


def test_template_gives_expected_jsonld() -> None:
    """The template should compile to the expected JSON-LD."""
    with COINCELL_TEMPLATE_PATH.open("r") as f:
        data = json.load(f)
    wb = dict_to_workbook(data)
    output_jsonld = convert_excel_to_jsonld(wb)

    with STANDARD_COINCELL_JSON_PATH.open("r") as f:
        expected_jsonld = json.load(f)

    assert normalize_jsonld(output_jsonld) == normalize_jsonld(expected_jsonld)
