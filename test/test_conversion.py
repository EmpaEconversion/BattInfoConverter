"""Test module for coin cell conversion."""

import json

import pytest
from conftest import CellFixtures, normalize_jsonld
from pyld import jsonld

from battinfoconverter_backend.json_convert import convert_excel_to_jsonld
from battinfoconverter_backend.templates.template_conversion import (
    dict_to_workbook,
    workbook_to_dict,
)


def test_regression(schema: CellFixtures) -> None:
    """The Excel conversion should match the expected JSON-LD output."""
    converted = convert_excel_to_jsonld(schema.excel, debug_mode=False, validate=False)
    assert normalize_jsonld(converted) == normalize_jsonld(schema.jsonld)


def test_valid_json(schema: CellFixtures) -> None:
    """The JSON-LD output should be valid."""
    converted = convert_excel_to_jsonld(schema.excel, validate=False)
    # This should run without errors
    json.dumps(converted)


def test_valid_jsonld(schema: CellFixtures) -> None:
    """The JSON-LD output should canonize without error."""
    converted = convert_excel_to_jsonld(schema.excel, validate=False)
    # This should run without errors
    jsonld.normalize(converted, {"algorithm": "URDNA2015", "format": "application/n-quads"})
    jsonld.expand(converted)


def test_no_warnings(schema: CellFixtures, caplog: pytest.LogCaptureFixture) -> None:
    """The standard excel should convert without warnings."""
    convert_excel_to_jsonld(schema.excel, validate=True)
    assert caplog.text == ""


def test_round_trip(schema: CellFixtures) -> None:
    """The template should survive roundtrips to excel and JSON."""
    data1 = schema.template
    wb1 = dict_to_workbook(data1)
    data2 = workbook_to_dict(wb1)
    wb2 = dict_to_workbook(data2)
    data3 = workbook_to_dict(wb2)
    assert data1 == data2
    assert data2 == data3


def test_template_does_not_warn(schema: CellFixtures, caplog: pytest.LogCaptureFixture) -> None:
    """The template should compile without any warnings."""
    wb = dict_to_workbook(schema.template)
    convert_excel_to_jsonld(wb)
    assert caplog.text == ""


def test_template_gives_expected_jsonld(schema: CellFixtures) -> None:
    """The template should compile to the expected JSON-LD."""
    wb = dict_to_workbook(schema.template)
    output_jsonld = convert_excel_to_jsonld(wb)
    assert normalize_jsonld(output_jsonld) == normalize_jsonld(schema.jsonld)


def test_empty_template(schema: CellFixtures) -> None:
    """Test that requesting empty template removes all non-essential values."""
    data1 = schema.template
    rows1 = data1["@Schema"]["data"]["Cell identification"]["rows"]
    rows1 = {v["Metadata"]: v["Value"] for v in rows1}
    wb1 = dict_to_workbook(data1, empty=True)
    data2 = workbook_to_dict(wb1)
    rows2 = data2["@Schema"]["data"]["Cell identification"]["rows"]
    rows2 = {v["Metadata"]: v["Value"] for v in rows2}
    kept = {"Cell type", "Schema name", "Schema version"}
    dropped = set(rows1.keys()) - kept
    for v in kept:
        assert rows1[v] is not None
        assert rows1[v] == rows2[v]
    for v in dropped:
        assert rows1[v] is not None
        assert rows2[v] is None

    for group in data1["@Schema"]["data"]:
        if group != "Cell identification":
            for row in data2["@Schema"]["data"][group]["rows"]:
                assert row["Value"] is None
