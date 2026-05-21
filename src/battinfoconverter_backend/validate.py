"""Funtions to validate JSON-LD outputs."""

import json
import logging
from difflib import get_close_matches
from pathlib import Path
from typing import Literal

from battinfoconverter_backend.auxiliary import LITERAL_PREDICATES

logger = logging.getLogger(__name__)
_MAPPED_TERMS: dict[str, list] | None = None

CONTEXT_DIR = Path(__file__).parent / "_context"


def get_context() -> dict:
    """Get the mappings of URL: list of terms."""
    global _MAPPED_TERMS  # noqa: PLW0603
    if _MAPPED_TERMS is not None:
        return _MAPPED_TERMS
    _MAPPED_TERMS = {}
    for file in CONTEXT_DIR.glob("*.json"):
        with file.open("r", encoding="utf-8") as f:
            data = json.load(f)
        _MAPPED_TERMS.update(data)
    return _MAPPED_TERMS


def find_similar_url(user_url: str) -> str | None:
    """Check if there is a close known URL."""
    known_urls = list(get_context().keys())
    matches = get_close_matches(user_url, known_urls, n=1, cutoff=0.6)
    if matches:
        return matches[0]
    return None


def map_context(
    context: str | list[str | dict[str, str]] | dict[str, str],
    existing_map: dict | None = None,
    errors: Literal["raise", "warn"] = "raise",
) -> dict:
    """Get all valid terms for the context, using the cached JSON context files."""
    if existing_map is None:
        existing_map = {}
    if isinstance(context, str):
        if "_base" not in existing_map:
            if context in get_context():
                existing_map["_base"] = get_context()[context]
            elif (context_ns := context.replace("/context", "#")) in get_context():
                existing_map["_base"] = get_context()[context_ns]
            else:
                msg = f"The base context URL ({context}) is not a known namespace of BattINFO converter."
                if errors == "raise":
                    raise ValueError(msg)
                logger.warning(msg)
        else:
            msg = "There are multiple 'default' vocabularies, you are only allowed one."
            if errors == "raise":
                raise ValueError(msg)
            logger.warning(msg)
    if isinstance(context, dict):
        for k, v in context.items():
            if v not in get_context():
                msg = f"The URL for '{k}' ({v}) is not a known namespace of BattINFO converter."
                close_match = find_similar_url(v)
                if close_match:
                    msg += f" Maybe you meant ({close_match})?"
                if errors == "raise":
                    raise ValueError(msg)
                logger.warning(msg)
                existing_map[k] = []
            else:
                existing_map[k] = get_context()[v]
    elif isinstance(context, list):
        for el in context:
            existing_map = map_context(el, existing_map, errors)
    return existing_map


def get_all_terms(obj: list | dict | str | float, seen: set | None = None) -> set:
    """Recursive search for all terms in JSON-LD."""
    if seen is None:
        seen = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "@context":
                continue  # Don't check context
            if k in {"@id", "@type"}:
                if isinstance(v, str):
                    seen.add(v)
                elif isinstance(v, list):
                    for el in v:
                        seen.add(el)
            elif not k.startswith("@"):
                seen.add(k)
                if k not in LITERAL_PREDICATES:
                    if isinstance(v, str):
                        seen.add(v)
                    elif isinstance(v, list):
                        for el in v:
                            if isinstance(el, str):
                                seen.add(el)
            get_all_terms(v, seen)
    elif isinstance(obj, list):
        for i in obj:
            get_all_terms(i, seen)
    return seen


def check_term_against_context(term: str, mapped_context: dict[str, list]) -> None:
    """Raise error if term is not in context, or not already IRI."""
    if term.startswith("http"):  # It is already an absolute IRI
        return
    if ":" in term:  # It is prefixed - check
        prefix, label = term.split(":", 1)
        if prefix not in mapped_context:
            msg = f"Prefix '{prefix}' is not in the context"
            raise ValueError(msg)
        if label not in mapped_context[prefix]:
            if not mapped_context[prefix]:
                msg = f"Term '{prefix}:{label}' was not found because '{prefix}' is empty"
                raise ValueError(msg)
            msg = f"Term '{prefix}:{label}' was not found in '{prefix}'"
            raise ValueError(msg)
        return
    # It is in the default namespace
    if "_base" not in mapped_context:
        msg = f"Term '{term}' has no prefix, but there is no default namespace"
        raise ValueError(msg)
    if term not in mapped_context["_base"]:
        msg = f"Term '{term}' was not found in the default namespace"
        raise ValueError(msg)


def validate_jsonld(doc: dict, errors: Literal["raise", "warn"] = "warn") -> None:
    """Check that terms in JSON-LD are known in context."""
    # Map out the context - URL: list of valid terms
    context = doc["@context"]
    mapped_context = map_context(context, errors=errors)

    # Get all the terms in the json-ld
    raw_terms = get_all_terms(doc)

    # Separate out prefixed and non-prefixed terms
    prefixed = [t for t in raw_terms if ":" in t]
    non_prefixed = [t for t in raw_terms if ":" not in t]
    terms = sorted(non_prefixed) + sorted(prefixed)

    # Check that every term is known
    for term in terms:
        try:
            check_term_against_context(term, mapped_context)
        except ValueError as e:  # noqa: PERF203
            if errors == "raise":
                raise
            logger.warning(str(e))
