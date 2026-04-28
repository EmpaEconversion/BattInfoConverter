"""Test module for standard Excel to JSON-LD conversion."""

import json

import pytest
from conftest import normalize_jsonld

from battinfoconverter_backend.json_convert import convert_excel_to_jsonld
from battinfoconverter_backend.templates.template_conversion import (
    COINCELL_TEMPLATE_PATH,
    dict_to_workbook,
    workbook_to_dict,
)


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


def test_template_gives_expected_jsonld(coincell_jsonld: dict) -> None:
    """The template should compile to the expected JSON-LD."""
    with COINCELL_TEMPLATE_PATH.open("r") as f:
        data = json.load(f)
    wb = dict_to_workbook(data)
    output_jsonld = convert_excel_to_jsonld(wb)
    assert normalize_jsonld(output_jsonld) == normalize_jsonld(coincell_jsonld)


def test_empty_template() -> None:
    """Test that asking for empty template actually gives empty template."""
    with COINCELL_TEMPLATE_PATH.open("r") as f:
        data1 = json.load(f)
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
