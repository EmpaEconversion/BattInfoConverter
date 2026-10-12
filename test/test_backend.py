"""Test module for backend behaviours."""

import io
from pathlib import Path

import pytest
from conftest import CellFixtures, normalize_jsonld
from openpyxl import Workbook, load_workbook

from battinfoconverter_backend.excel_tools import ExcelContainer, _canonical_sheets
from battinfoconverter_backend.json_convert import convert_excel_to_jsonld
from battinfoconverter_backend.templates.template_conversion import (
    dict_to_workbook,
)
from battinfoconverter_backend.validate import validate_jsonld


def test_standard_battinfo_hardcoded_header(tmpdir: Path, coincell: CellFixtures) -> None:
    """Check that coin cell Excel conversion matches expected JSON-LD output when using hardcoded header.

    Required for backwards compatibility.
    """
    new_excel = tmpdir / "NotOntologizeTest.xlsx"
    values_to_update = {
        "Cell type": "NotOntologize",
        "Cell ID": "NotOntologize",
        "Date of cell assembly": "NotOntologize",
        "Institution/company": "NotOntologize",
        "Scientist/technician/operator": "NotOntologize",
        "Project": "Comment",
        "Assembled manually or by robot": "Comment",
        "Schema name": "Comment",
        "Schema version": "Comment",
    }
    wb = load_workbook(coincell.excel)
    sheet = wb["@Schema"]
    headings = [cell.value for cell in sheet[1]]
    link_column = headings.index("Ontology link")
    for row in sheet.iter_rows(min_row=2):
        col_a = row[0].value
        if col_a in values_to_update:
            row[link_column].value = values_to_update[col_a]
    wb.save(new_excel)  # Overwrites in place, or use a new name
    converted = convert_excel_to_jsonld(new_excel, debug_mode=False, validate=False)
    assert normalize_jsonld(converted) == normalize_jsonld(coincell.jsonld)


def test_conversion_different_inputs(schema: CellFixtures) -> None:
    """Users should be able to read files in different ways."""
    # pathlib.Path object
    res1 = convert_excel_to_jsonld(schema.excel, validate=False)

    # String object
    res2 = convert_excel_to_jsonld(str(schema.excel), validate=False)

    # Buffered reader object
    with schema.excel.open("rb") as f:
        excel_bytesio = io.BytesIO(f.read())
        res3 = convert_excel_to_jsonld(f, validate=False)

    # Bytes IO object
    res4 = convert_excel_to_jsonld(excel_bytesio, validate=False)

    # Already loaded workbook
    res5 = convert_excel_to_jsonld(load_workbook(schema.excel), validate=False)

    # Should not affect the results
    assert res1 == res2 == res3 == res4 == res5


def test_against_cached_context(coincell: CellFixtures) -> None:
    """Make sure all terms are mapped in the cached context."""
    # The standard filled excel template must pass
    converted = convert_excel_to_jsonld(coincell.excel, validate=True)
    validate_jsonld(converted, errors="raise")

    # Validation should not modify original dict
    assert converted == convert_excel_to_jsonld(coincell.excel, validate=True)

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

    bad_jsonld = converted.copy()
    bad_jsonld["hasComponent"] = "ThisDoesNotExist"
    with pytest.raises(ValueError, match="'ThisDoesNotExist' was not found"):
        validate_jsonld(bad_jsonld, errors="raise")


def test_bad_jsonld_context(caplog: pytest.LogCaptureFixture) -> None:
    """Check if expected validation warnings/errors trigger."""
    doc = {
        "@context": [
            "https://w3id.org/emmo/domain/battery/context",
            "https://w3id.org/emmo/domain/electrochemistry/context",
        ],
        "@type": "CoinCell",
    }
    with pytest.raises(ValueError, match="There are multiple 'default' vocabularies, you are only allowed one"):
        validate_jsonld(doc, errors="raise")

    doc = {
        "@context": {
            "battery": "https://w3id.org/emmo/domain/batterie",
        },
        "@type": "CoinCell",
    }
    with pytest.raises(ValueError, match=r"Maybe you meant (https://w3id.org/emmo/domain/battery#)?"):
        validate_jsonld(doc, errors="raise")

    caplog.clear()
    doc = {
        "@context": {
            "missing": "https://w3id.org/emmo/domain/somethingwrong",
        },
        "@type": "CoinCell",
        "hasComponent": {
            "@id": "missing:StuffThatCannotBeFound",
        },
    }
    validate_jsonld(doc, errors="warn")
    # The URL does not end in a general delimiter, so JSON-LD would not expand
    # 'missing:...' at all and the entry can only define a single term
    assert "'CoinCell' has no prefix, but there is no default namespace" in caplog.text
    assert "'missing' maps to a single term, so 'missing:StuffThatCannotBeFound' is not expanded" in caplog.text


def test_redundant_prefix(caplog: pytest.LogCaptureFixture) -> None:
    """Check that prefixing a term already in the default context warns."""
    doc = {
        "@context": [
            "https://w3id.org/emmo/domain/battery/context",
            {"emmo": "https://w3id.org/emmo#", "schema": "https://schema.org/"},
        ],
        "@type": ["CoinCell", "emmo:Hertz", "schema:Person"],
        "schema:manufacturer": {"@type": "schema:Organization"},
        "hasMeasurementUnit": "emmo:Volt",
    }
    validate_jsonld(doc, errors="warn")
    assert "Term 'emmo:Hertz' is already in the default context - you can use 'Hertz' without the prefix" in caplog.text
    # schema terms share labels with the default context (Person, Manufacturer, ...)
    # but expand to different IRIs, so they must not warn
    assert "'schema:Person' is already in the default context" not in caplog.text
    assert "'schema:manufacturer' is already in the default context" not in caplog.text
    # String values are IRI references, where a bare term would not resolve via the context
    assert "'emmo:Volt' is already in the default context" not in caplog.text


def test_bad_prefixed_unit(coincell: CellFixtures, caplog: pytest.LogCaptureFixture) -> None:
    """Check that unit missing from prefixed namespace warns."""
    template = coincell.template.copy()
    template["@Units"]["data"].append({"Unit": "foo", "Unit class": "unit:thisDoesNotExist"})
    template["@Schema"]["data"]["Positive electrode (cathode when battery is discharged)"]["rows"].append(
        {
            "Metadata": "Some made up quantity with a unit missing an IRI",
            "Value": 1.2345,
            "Unit": "foo",
            "Priority": "recommended",
            "Ontology link": "hasPositiveElectrode-hasCurrentCollector-hasMeasuredProperty-Density",
            "Note": None,
        },
    )
    wb = dict_to_workbook(template)
    convert_excel_to_jsonld(wb, validate=True)
    assert "Term 'unit:thisDoesNotExist' was not found in 'unit'" in caplog.text


def test_bad_default_unit(coincell: CellFixtures, caplog: pytest.LogCaptureFixture) -> None:
    """Check that unit missing from default namespace warns."""
    template = coincell.template.copy()
    template["@Units"]["data"].append({"Unit": "foo", "Unit class": "thisDoesNotExist"})
    template["@Schema"]["data"]["Positive electrode (cathode when battery is discharged)"]["rows"].append(
        {
            "Metadata": "Some made up quantity with a unit missing an IRI",
            "Value": 1.2345,
            "Unit": "foo",
            "Priority": "recommended",
            "Ontology link": "hasPositiveElectrode-hasCurrentCollector-hasMeasuredProperty-Density",
            "Note": None,
        },
    )
    wb = dict_to_workbook(template)
    convert_excel_to_jsonld(wb, validate=True)
    assert "Term 'thisDoesNotExist' was not found in the default namespace" in caplog.text


def test_missing_unit(coincell: CellFixtures) -> None:
    """Check that missing unit in @Units tab errors."""
    template = coincell.template.copy()
    template["@Schema"]["data"]["Positive electrode (cathode when battery is discharged)"]["rows"].append(
        {
            "Metadata": "Some made up quantity with a unit missing an IRI",
            "Value": 1.2345,
            "Unit": "foo",
            "Priority": "recommended",
            "Ontology link": "hasPositiveElectrode-hasCurrentCollector-hasMeasuredProperty-Density",
            "Note": None,
        },
    )
    wb = dict_to_workbook(template)
    with pytest.raises(ValueError, match=r"The unit 'foo' was not found in the @Units tab."):
        convert_excel_to_jsonld(wb, validate=True)


# Headings the loader should resolve to the same canonical columns: the current
# names, the names older templates shipped, lower case, and wordings not seen yet
HEADING_STYLES = {
    "current": {
        "units": ["Unit", "Unit class"],
        "context": ["Term", "IRI"],
        "predicates": ["Predicate", "Default class"],
        "individuals": ["Name", "Class", "IRI"],
        "note": "Note",
    },
    "legacy": {
        "units": ["Item", "Key"],
        "context": ["Item", "Key"],
        "predicates": ["Item", "Key"],
        "individuals": ["Name", "Type", "ID"],
        "note": "Comment",
    },
    "lower case": {
        "units": ["unit", "unit class"],
        "context": ["term", "iri"],
        "predicates": ["predicate", "default class"],
        "individuals": ["name", "class", "iri"],
        "note": "note",
    },
    "unseen wording": {
        "units": ["Unit symbol", "Unit IRI"],
        "context": ["Prefix", "Namespace IRI"],
        "predicates": ["Predicate", "Default type"],
        "individuals": ["Name", "Class", "Identifier"],
        "note": "Note",
    },
}


def _workbook_with_headings(style: dict) -> Workbook:
    """A minimal workbook whose sheets carry one style of column headings."""
    wb = Workbook()
    ws = wb.active
    ws.title = "@Schema"
    ws.append(["Metadata", "Value", "Unit", "Priority", style["note"], "Ontology link"])
    ws.append(["Thickness", 12, "xx", "optional", "a note", "hasNegativeElectrode-hasMeasuredProperty-Thickness"])
    ws = wb.create_sheet("@Context")
    ws.append(style["context"])
    ws.append(["unit", "https://qudt.org/vocab/unit/"])
    ws = wb.create_sheet("@Predicates")
    ws.append(style["predicates"])
    ws.append(["hasNegativeElectrode", "NegativeElectrode"])
    ws = wb.create_sheet("@Individuals")
    ws.append(style["individuals"])
    ws.append(["Empa", "schema:Organization", "http://www.wikidata.org/entity/Q683116"])
    ws = wb.create_sheet("@Units")
    ws.append(style["units"])
    ws.append(["xx", "MilliMetre"])
    return wb


@pytest.mark.parametrize("name", list(HEADING_STYLES))
def test_column_headings_resolve(name: str) -> None:
    """Every heading style should load to the same canonical columns and values."""
    container = ExcelContainer(_workbook_with_headings(HEADING_STYLES[name]))
    assert container.data["unit_map"] == {"xx": "MilliMetre"}
    assert list(container.data["context_toplevel"].columns)[:2] == ["Term", "IRI"]
    assert list(container.data["context_connector"].columns)[:2] == ["Predicate", "Default class"]
    assert "Note" in container.data["schema"].columns
    assert container.data["individual_names"] == {"Empa"}
    assert container.data["individual_types"] == {"Empa": "schema:Organization"}
    assert container.data["unique_id_map"] == {"Empa": "http://www.wikidata.org/entity/Q683116"}


def test_legacy_sheet_names() -> None:
    """Alternative spellings of sheet names are accepted."""
    res = _canonical_sheets(
        ["schema", "Context - TopLevel", "Context - Connector", "Unique ID", "Ontology - Unit"],
    )
    assert res == {
        "@Schema": "schema",
        "@Context": "Context - TopLevel",
        "@Predicates": "Context - Connector",
        "@Classes": "Unique ID",
        "@Units": "Ontology - Unit",
    }

    res = _canonical_sheets(
        ["@ScHeMa  ", " @ rEfErEnCeS ", "cONTEXT   ", "@@PREDICATES", " classes ", "@individuals", "@UNITS"],
    )
    assert res == {
        "@Schema": "@ScHeMa  ",
        "@References": " @ rEfErEnCeS ",
        "@Context": "cONTEXT   ",
        "@Predicates": "@@PREDICATES",
        "@Classes": " classes ",
        "@Individuals": "@individuals",
        "@Units": "@UNITS",
    }
