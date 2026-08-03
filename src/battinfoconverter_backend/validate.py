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
        if file.name == "literal_predicates.json":
            continue
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
            # Expanded term definitions: track @vocab-typed properties, whose string
            # values resolve through the context like keys and @type values do
            if isinstance(v, dict):
                if v.get("@type") == "@vocab":
                    existing_map.setdefault("_vocab", set()).add(k)
                continue
            existing_map.setdefault("_urls", {})[k] = v
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


def get_all_terms(
    obj: list | dict | str | float,
    vocab_terms: set | None = None,
    iri_terms: set | None = None,
    vocab_props: frozenset | set = frozenset(),
) -> tuple[set, set]:
    """Recursive search for all terms in JSON-LD.

    Returns (vocab_terms, iri_terms): keys, @type values, and string values of
    @vocab-typed properties resolve through context term definitions, while @id
    and other string values only expand prefixes.
    """
    if vocab_terms is None:
        vocab_terms = set()
    if iri_terms is None:
        iri_terms = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "@context":
                continue  # Don't check context
            if k in {"@id", "@type"}:
                target = vocab_terms if k == "@type" else iri_terms
                if isinstance(v, str):
                    target.add(v)
                elif isinstance(v, list):
                    for el in v:
                        target.add(el)
            elif not k.startswith("@"):
                vocab_terms.add(k)
                if k not in LITERAL_PREDICATES:
                    target = vocab_terms if k in vocab_props else iri_terms
                    if isinstance(v, str):
                        target.add(v)
                    elif isinstance(v, list):
                        for el in v:
                            if isinstance(el, str):
                                target.add(el)
            get_all_terms(v, vocab_terms, iri_terms, vocab_props)
    elif isinstance(obj, list):
        for i in obj:
            get_all_terms(i, vocab_terms, iri_terms, vocab_props)
    return vocab_terms, iri_terms


def check_term_against_context(term: str, mapped_context: dict, *, warn_redundant_prefix: bool = True) -> None:
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
        # EMMO-family namespaces share labels (and IRIs) with the default context,
        # so the prefix is redundant; other namespaces (e.g. schema) only share labels
        prefix_url = mapped_context.get("_urls", {}).get(prefix, "")
        if (
            warn_redundant_prefix
            and prefix_url.startswith("https://w3id.org/emmo")
            and label in mapped_context.get("_base", [])
        ):
            logger.warning(
                "Term '%s' is already in the default context - you can use '%s' without the prefix.",
                term,
                label,
            )
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
    vocab_props = mapped_context.get("_vocab", frozenset())
    vocab_terms, iri_terms = get_all_terms(doc, vocab_props=vocab_props)
    raw_terms = vocab_terms | iri_terms

    # Separate out prefixed and non-prefixed terms
    prefixed = [t for t in raw_terms if ":" in t]
    non_prefixed = [t for t in raw_terms if ":" not in t]
    terms = sorted(non_prefixed) + sorted(prefixed)

    # Check that every term is known
    for term in terms:
        try:
            # A prefix is only redundant in vocab position; @id/string values need it to expand
            check_term_against_context(term, mapped_context, warn_redundant_prefix=term not in iri_terms)
        except ValueError as e:  # noqa: PERF203
            if errors == "raise":
                raise
            logger.warning(str(e))
