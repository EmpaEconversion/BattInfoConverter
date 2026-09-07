"""Test module for coin cell conversion."""

import json

import pytest
from conftest import CellFixtures, normalize_jsonld
from openpyxl import load_workbook
from pyld import jsonld

from battinfoconverter_backend.json_convert import convert_excel_to_jsonld
from battinfoconverter_backend.templates.template_conversion import (
    dict_to_workbook,
    workbook_to_dict,
)


def _filter_warnings(warnings: list[str]) -> list[str]:
    """Filter out non-critical, acceptable warnings."""
    return [w for w in warnings if " recommended values: " not in w and "This is a 'schema:manufacturer' - " not in w]


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


def test_units_expand_to_real_iris(schema: CellFixtures) -> None:
    """Unit values must expand to ontology IRIs, not document-relative ones."""
    converted = convert_excel_to_jsonld(schema.excel, validate=False)
    expanded = jsonld.expand(converted)
    unit_predicate = "https://w3id.org/emmo#EMMO_bed1d005_b04e_4a90_94cf_02bc678a8569"

    def collect(obj: dict | list, found: list) -> list:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == unit_predicate:
                    found.extend(el["@id"] for el in v if isinstance(el, dict) and "@id" in el)
                collect(v, found)
        elif isinstance(obj, list):
            for el in obj:
                collect(el, found)
        return found

    unit_iris = collect(expanded, [])
    assert unit_iris
    for iri in unit_iris:
        assert iri.startswith(("https://w3id.org/emmo", "https://qudt.org/vocab/unit/")), iri


def test_no_warnings(schema: CellFixtures, caplog: pytest.LogCaptureFixture) -> None:
    """The standard excel should convert without warnings."""
    convert_excel_to_jsonld(schema.excel, validate=True)
    warnings = caplog.text.splitlines()
    assert not _filter_warnings(warnings)


def test_round_trip_from_json(schema: CellFixtures) -> None:
    """The template should survive roundtrip starting from JSON template."""
    data1 = schema.template
    wb1 = dict_to_workbook(data1)
    data2 = workbook_to_dict(wb1)
    wb2 = dict_to_workbook(data2)
    data3 = workbook_to_dict(wb2)
    assert data1 == data2
    assert data2 == data3


def test_round_trip_from_excel(schema: CellFixtures) -> None:
    """The template should survive roundtrip starting from Excel test file."""
    wb1 = load_workbook(schema.excel)
    data1 = workbook_to_dict(wb1)
    wb2 = dict_to_workbook(data1)
    data2 = workbook_to_dict(wb2)

    data3 = schema.template  # must also match the template

    assert data1 == data2
    assert data2 == data3


def test_template_does_not_warn(schema: CellFixtures, caplog: pytest.LogCaptureFixture) -> None:
    """The template should compile without any warnings."""
    wb = dict_to_workbook(schema.template)
    convert_excel_to_jsonld(wb)
    warnings = caplog.text.splitlines()
    assert not _filter_warnings(warnings)


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
