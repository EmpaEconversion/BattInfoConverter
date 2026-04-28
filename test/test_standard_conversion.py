"""Test module for standard Excel to JSON-LD conversion."""

import io
import json
from pathlib import Path

import pytest
from conftest import normalize_jsonld
from openpyxl import load_workbook
from pyld import jsonld

from battinfoconverter_backend.json_convert import convert_excel_to_jsonld
from battinfoconverter_backend.validate import validate_jsonld


def test_standard_battinfo(coincell_excel_path: Path, coincell_jsonld: dict) -> None:
    """Check that coin cell Excel conversion matches expected JSON-LD output."""
    converted = convert_excel_to_jsonld(coincell_excel_path, debug_mode=False, validate=False)
    assert normalize_jsonld(converted) == normalize_jsonld(coincell_jsonld)


def test_standard_battinfo_hardcoded_header(tmpdir: Path, coincell_excel_path: Path, coincell_jsonld: dict) -> None:
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
    wb = load_workbook(coincell_excel_path)
    sheet = wb["@Schema"]
    for row in sheet.iter_rows():
        col_a = row[0].value
        if col_a in values_to_update:
            row[4].value = values_to_update[col_a]
    wb.save(new_excel)  # Overwrites in place, or use a new name
    converted = convert_excel_to_jsonld(new_excel, debug_mode=False, validate=False)
    assert normalize_jsonld(converted) == normalize_jsonld(coincell_jsonld)


def test_standard_catinfo(catalysis_excel_path: Path, catalysis_jsonld: dict) -> None:
    """Check that catalysis Excel conversion matches expected JSON-LD output."""
    converted = convert_excel_to_jsonld(catalysis_excel_path, validate=False)
    assert normalize_jsonld(converted) == normalize_jsonld(catalysis_jsonld)


def test_valid_json(coincell_excel_path: Path) -> None:
    """Make sure the JSON-LD output is valid."""
    converted = convert_excel_to_jsonld(coincell_excel_path, validate=False)
    # This should run without errors
    json.dumps(converted)


def test_conversion_different_inputs(coincell_excel_path: Path) -> None:
    """Users should be able to read files in different ways."""
    # pathlib.Path object
    res1 = convert_excel_to_jsonld(coincell_excel_path, validate=False)

    # String object
    res2 = convert_excel_to_jsonld(str(coincell_excel_path), validate=False)

    # Buffered reader object
    with coincell_excel_path.open("rb") as f:
        excel_bytesio = io.BytesIO(f.read())
        res3 = convert_excel_to_jsonld(f, validate=False)

    # Bytes IO object
    res4 = convert_excel_to_jsonld(excel_bytesio, validate=False)

    # Already loaded workbook
    res5 = convert_excel_to_jsonld(load_workbook(coincell_excel_path), validate=False)

    # Should not affect the results
    assert res1 == res2 == res3 == res4 == res5


def test_valid_jsonld(coincell_excel_path: Path) -> None:
    """Check that the JSON-LD output canonizes without error."""
    converted = convert_excel_to_jsonld(coincell_excel_path, validate=False)
    # This should run without errors
    jsonld.normalize(converted, {"algorithm": "URDNA2015", "format": "application/n-quads"})
    jsonld.expand(converted)


def test_against_cached_context(coincell_excel_path: Path) -> None:
    """Make sure all terms are mapped in the cached context."""
    # The standard filled excel template must pass
    converted = convert_excel_to_jsonld(coincell_excel_path, validate=True)
    validate_jsonld(converted, errors="raise")

    # Validation should not modify original dict
    assert converted == convert_excel_to_jsonld(coincell_excel_path, validate=True)

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
    assert "The URL for 'missing' (https://w3id.org/emmo/domain/somethingwrong) is not a known namespace" in caplog.text
    assert "'CoinCell' has no prefix, but there is no default namespace" in caplog.text
    assert "Term 'missing:StuffThatCannotBeFound' was not found because 'missing' is empty" in caplog.text
