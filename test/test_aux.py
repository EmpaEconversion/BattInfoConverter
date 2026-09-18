"""Unit test auxiliary functions."""

from datetime import datetime

from conftest import EXCEL_PATHS

from battinfoconverter_backend.auxiliary import add_to_structure, coerce_date_to_iso
from battinfoconverter_backend.excel_tools import ExcelContainer
from battinfoconverter_backend.registry import Registry


def test_date_coercion() -> None:
    """Check that date coercion works as expected."""
    assert coerce_date_to_iso("2026/01/31") == "2026-01-31"
    assert coerce_date_to_iso("2026-01-31") == "2026-01-31"
    assert coerce_date_to_iso("2026.01.31") == "2026-01-31"
    assert coerce_date_to_iso("31/01/2026") == "2026-01-31"
    assert coerce_date_to_iso("31-01-2026") == "2026-01-31"
    assert coerce_date_to_iso("31.01.2026") == "2026-01-31"

    assert coerce_date_to_iso("   2026/01/31    ") == "2026-01-31"

    assert coerce_date_to_iso(datetime.fromisoformat("2026-01-31")) == "2026-01-31"


def _build(rows: list[tuple[str, float | str, str, str]]) -> dict:
    """Convert (link, value, unit, metadata) rows into a JSON-LD fragment."""
    container = Registry(ExcelContainer(EXCEL_PATHS["flowcell"]))
    jsonld: dict = {}
    for link, value, unit, metadata in rows:
        add_to_structure(jsonld, link.split("-"), value, unit, container, metadata=metadata)
    return jsonld


def test_comment_targets_measured_property_by_type() -> None:
    """A 'type|<Class>' comment attaches to the quantity of that type, not a nested key."""
    jsonld = _build(
        [
            ("hasCatholyte-hasMeasuredProperty-Volume", 30, "mL", "Volume"),
            ("hasCatholyte-hasMeasuredProperty-VolumeFlowRate", 60, "mL/min", "Flow rate"),
            (
                "hasCatholyte-hasMeasuredProperty-type|VolumeFlowRate-rdfs:comment",
                "calibrated",
                "No Unit",
                "Flow rate cal",
            ),
        ]
    )
    volume, flow_rate = jsonld["hasCatholyte"]["hasMeasuredProperty"]
    assert "rdfs:comment" not in volume
    assert "VolumeFlowRate" not in flow_rate
    assert flow_rate["rdfs:comment"] == "Flow rate cal: calibrated"


def test_comment_distinguishes_duplicate_measured_properties() -> None:
    """With two quantities of the same type, the metadata label picks the target."""
    rows = [
        ("hasPositiveElectrode-hasSubstrate-hasMeasuredProperty-Thickness", 560, "um", "Substrate thickness"),
        (
            "hasPositiveElectrode-hasSubstrate-hasMeasuredProperty-Thickness",
            450,
            "um",
            "Thickness in cell under compression",
        ),
    ]
    link = "hasPositiveElectrode-hasSubstrate-hasMeasuredProperty-type|Thickness-rdfs:comment"

    jsonld = _build([*rows, (link, "measured under load", "No Unit", "Thickness in cell comment")])
    uncompressed, compressed = jsonld["hasPositiveElectrode"]["hasSubstrate"]["hasMeasuredProperty"]
    assert "rdfs:comment" not in uncompressed
    assert compressed["rdfs:comment"] == "Thickness in cell comment: measured under load"

    jsonld = _build([*rows, (link, "as delivered", "No Unit", "Substrate thickness comment")])
    uncompressed, compressed = jsonld["hasPositiveElectrode"]["hasSubstrate"]["hasMeasuredProperty"]
    assert uncompressed["rdfs:comment"] == "Substrate thickness comment: as delivered"
    assert "rdfs:comment" not in compressed
