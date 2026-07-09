"""Pytest set up and helper functions."""

import copy
import json
from decimal import Decimal
from functools import cached_property
from pathlib import Path

import pytest
from pyld import jsonld

from battinfoconverter_backend.templates.template_conversion import (
    COINCELL_TEMPLATE_PATH,
    ELECTROLYSIS_TEMPLATE_PATH,
    FLOWCELL_TEMPLATE_PATH,
)
from battinfoconverter_backend.validate import get_context

jsonld.set_document_loader(jsonld.requests_document_loader())

IGNORED_COMMENT_PREFIXES = (
    "BattINFO Converter version:",
    "Software credit:",
    "BattINFO CoinCellSchema version:",
    "Schema version:",
)

DATA_DIR = Path(__file__).resolve().parent / "data"

CELL_TYPES = ["coincell", "flowcell", "electrolysis"]

EXCEL_PATHS = {
    "coincell": DATA_DIR / "coincell_excel_schema.xlsx",
    "flowcell": DATA_DIR / "flowcell_excel_schema.xlsx",
    "electrolysis": DATA_DIR / "electrolysis_excel_schema.xlsx",
}

JSONLD_PATHS = {
    "coincell": DATA_DIR / "coincell_jsonld_result.json",
    "flowcell": DATA_DIR / "flowcell_jsonld_result.json",
    "electrolysis": DATA_DIR / "electrolysis_jsonld_result.json",
}

TEMPLATE_PATHS = {
    "coincell": COINCELL_TEMPLATE_PATH,
    "flowcell": FLOWCELL_TEMPLATE_PATH,
    "electrolysis": ELECTROLYSIS_TEMPLATE_PATH,
}


REF_DIR = Path(__file__).resolve().parent.parent / "Excel for reference"

REGRESSION_FILES = [
    "241125_Battery2030+_CoinCellBattery_Schema_Ontologized_1.0.0_filled.xlsx",
    "250515_241125_Battery2030+_CoinCellBattery_Schema_Ontologized_1.1.2_filled.xlsx",
    "250515_241125_Battery2030+_CoinCellBattery_Schema_Ontologized_1.1.7_filled.xlsx",
    "250515_241125_Battery2030+_CoinCellBattery_Schema_Ontologized_1.1.8_filled.xlsx",
    "BattINFO_converter_standard_Excel_version_1.1.9_filled.xlsx",
    "BattINFO_converter_standard_Excel_version_1.1.10.xlsx",
    "BattINFO_converter_standard_Excel_version_1.1.11_filled.xlsx",
    "BattINFO_converter_standard_Excel_version_1.1.12_filled.xlsx",
    "BattINFO_converter_standard_Excel_version_1.1.13_filled.xlsx",
    "BattINFO_converter_standard_Excel_version_1.1.14_filled.xlsx",
    "BattINFO_converter_standard_Excel_version_1.1.15_filled.xlsx",
    "BattINFO_converter_standard_Excel_version_1.1.16_filled.xlsx",
    "BattINFO_converter_standard_Excel_version_1.1.17_filled.xlsx",
]


class CellFixtures:
    """Lazy fixtures for tests."""

    def __init__(self, request: pytest.FixtureRequest) -> None:
        """Initialize object, don't load anything."""
        self._param = request.param

    @cached_property
    def excel(self) -> Path:
        """Get path to excel schema."""
        return EXCEL_PATHS[self._param]

    @cached_property
    def jsonld(self) -> dict:
        """Get path to expected JSON-LD output."""
        path = JSONLD_PATHS[self._param]
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    @cached_property
    def template(self) -> dict:
        """Get path to JSON template."""
        path = TEMPLATE_PATHS[self._param]
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)


@pytest.fixture(params=CELL_TYPES)
def schema(request: pytest.FixtureRequest) -> CellFixtures:
    """Get object to access all fixtures for a given cell type."""
    return CellFixtures(request)


@pytest.fixture(params=["coincell"])
def coincell(request: pytest.FixtureRequest) -> CellFixtures:
    """Get object to access all fixtures for the coin cell."""
    return CellFixtures(request)


@pytest.fixture(params=REGRESSION_FILES)
def old_schema(request: pytest.FixtureRequest) -> Path:
    """Get path to old xlsx templates."""
    return Path(REF_DIR / request.param)


def coerce_decimals(value: Decimal | float | dict | list) -> float | dict | list:
    """Recursively convert ``Decimal`` instances within ``value`` to floats."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: coerce_decimals(item) for key, item in value.items()}
    if isinstance(value, list):
        return [coerce_decimals(item) for item in value]
    return value


def normalize_jsonld(payload: dict) -> dict:
    """Return a copy of ``payload`` with version metadata removed for comparison."""
    normalized = coerce_decimals(copy.deepcopy(payload))
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
