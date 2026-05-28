"""New backend versions should not crash reading old schemas."""

from pathlib import Path

from battinfoconverter_backend import convert_excel_to_jsonld


def test_conversion_old_schema(old_schema: Path) -> None:
    """Conversion should run without errors.

    Warnings / outputs may change with new backend versions.
    """
    res = convert_excel_to_jsonld(old_schema)
    assert isinstance(res, dict)
    assert len(res) >= 13
    assert "@context" in res
    assert "@type" in res
    terms = [
        "hasPositiveElectrode",
        "hasNegativeElectrode",
        "hasElectrolyte",
        "hasSeparator",
        "hasCase",
    ]
    for term in terms:
        assert term in res
        assert "@type" in res[term]
        assert len(res[term]) >= 4
