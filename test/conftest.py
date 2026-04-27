"""Pytest set up and helper functions."""

import copy
from decimal import Decimal

from pyld import jsonld

jsonld.set_document_loader(jsonld.requests_document_loader())

IGNORED_COMMENT_PREFIXES = (
    "BattINFO Converter version:",
    "Software credit:",
    "BattINFO CoinCellSchema version:",
    "Schema version:",
)


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
