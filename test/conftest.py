"""Pytest set up and helper functions."""

import copy
import json
from decimal import Decimal
from functools import cached_property
from pathlib import Path

import pytest
from pyld import jsonld

from battinfoconverter_backend.templates.template_conversion import COINCELL_TEMPLATE_PATH

jsonld.set_document_loader(jsonld.requests_document_loader())

IGNORED_COMMENT_PREFIXES = (
    "BattINFO Converter version:",
    "Software credit:",
    "BattINFO CoinCellSchema version:",
    "Schema version:",
)

FIXTURE_DIR = Path(__file__).resolve().parent

CELL_TYPES = ["coincell"]

EXCEL_PATHS = {
    "coincell": FIXTURE_DIR / "standard_coincell_excel_schema.xlsx",
}

JSONLD_PATHS = {
    "coincell": FIXTURE_DIR / "standard_coincell_json_schema.json",
}

TEMPLATE_PATHS = {
    "coincell": COINCELL_TEMPLATE_PATH,
}


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
        with path.open("r") as f:
            return json.load(f)

    @cached_property
    def template(self) -> dict:
        """Get path to JSON template."""
        path = TEMPLATE_PATHS[self._param]
        with path.open("r") as f:
            return json.load(f)


@pytest.fixture(params=CELL_TYPES)
def schema(request: pytest.FixtureRequest) -> CellFixtures:
    """Get object to access all fixtures for a given cell type."""
    return CellFixtures(request)


@pytest.fixture(params=["coincell"])
def coincell(request: pytest.FixtureRequest) -> CellFixtures:
    """Get object to access all fixtures for the coin cell."""
    return CellFixtures(request)


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
