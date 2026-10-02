"""Funtions to validate JSON-LD outputs."""

import json
import logging
from collections.abc import Iterable
from difflib import get_close_matches
from pathlib import Path
from typing import Literal

from battinfoconverter_backend.auxiliary import LITERAL_PREDICATES

logger = logging.getLogger(__name__)
_MAPPED_TERMS: dict[str, list] | None = None
_DECLARED_PREFIXES: dict[str, dict[str, str]] | None = None

CONTEXT_DIR = Path(__file__).parent / "_context"

ErrorMode = Literal["raise", "warn", "ignore"]

# Above this similarity to a known namespace, an unknown one is read as a typo of it
# rather than as a namespace of the user's own
NAMESPACE_TYPO_CUTOFF = 0.85

# How close a known term must be to a value before it is offered as 'did you mean'
SUGGESTION_CUTOFF = 0.8

# JSON-LD only allows prefixes with namespace IRIs ending with these characters (RFC 3986)
GEN_DELIMS = (":", "/", "?", "#", "[", "]", "@")


def _load_cache() -> tuple[dict, dict]:
    """Read the cached context files into the term and prefix maps."""
    global _MAPPED_TERMS, _DECLARED_PREFIXES
    if _MAPPED_TERMS is None or _DECLARED_PREFIXES is None:
        terms: dict[str, list] = {}
        declared: dict[str, dict[str, str]] = {}
        for file in CONTEXT_DIR.glob("*.json"):
            if file.name == "literal_predicates.json":
                continue
            with file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            prefixes = data.pop("_prefixes", {})
            terms.update(data)
            for namespace in data:
                declared[namespace] = prefixes
        _MAPPED_TERMS, _DECLARED_PREFIXES = terms, declared
    return _MAPPED_TERMS, _DECLARED_PREFIXES


def get_context() -> dict:
    """Get the mappings of URL: list of terms."""
    return _load_cache()[0]


def get_declared_prefixes(namespace: str) -> dict[str, str]:
    """Get the prefixes that the context of `namespace` declares itself."""
    return _load_cache()[1].get(namespace, {})


def find_similar_url(user_url: str, cutoff: float = 0.6) -> str | None:
    """Check if there is a close known URL."""
    known_urls = list(get_context().keys())
    matches = get_close_matches(user_url, known_urls, n=1, cutoff=cutoff)
    if matches:
        return matches[0]
    return None


def _add_declared_prefixes(existing_map: dict, namespace: str) -> None:
    """Note prefixes the remote context declares, e.g. dcterms, so terms using them expand.

    There are no cached term lists for these namespaces, so their terms are not checked.
    """
    declared = get_declared_prefixes(namespace)
    if declared:
        existing_map.setdefault("_declared", {}).update(declared)


def _report(msg: str, errors: ErrorMode) -> None:
    """Raise, warn, or stay quiet about a problem."""
    if errors == "raise":
        raise ValueError(msg)
    if errors == "warn":
        logger.warning(msg)


def map_context(
    context: str | list[str | dict[str, str]] | dict[str, str],
    existing_map: dict | None = None,
    errors: ErrorMode = "raise",
) -> dict:
    """Get all valid terms for the context, using the cached JSON context files."""
    if existing_map is None:
        existing_map = {}
    if isinstance(context, str):
        if "_base" not in existing_map:
            if context in get_context():
                existing_map["_base"] = get_context()[context]
                _add_declared_prefixes(existing_map, context)
            elif (context_ns := context.replace("/context", "#")) in get_context():
                existing_map["_base"] = get_context()[context_ns]
                _add_declared_prefixes(existing_map, context_ns)
            else:
                msg = f"The base context URL ({context}) is not a known namespace of BattINFO converter."
                _report(msg, errors)
        else:
            msg = "There are multiple 'default' vocabularies, you are only allowed one."
            _report(msg, errors)
    if isinstance(context, dict):
        for k, v in context.items():
            # Expanded term definitions: track @vocab-typed properties, whose string
            # values resolve through the context like keys and @type values do
            if isinstance(v, dict):
                if v.get("@type") == "@vocab":
                    existing_map.setdefault("_vocab", set()).add(k)
                continue
            known = get_context()
            if v in known:  # A namespace we hold the term list for
                existing_map.setdefault("_urls", {})[k] = v
                existing_map[k] = known[v]
                continue
            # A URL reaching into a namespace we know names one term of it
            if any(v.startswith(namespace) for namespace in known):
                existing_map.setdefault("_terms", set()).add(k)
                continue
            # Nearly a known namespace, so probably a typo
            if close_match := find_similar_url(v, cutoff=NAMESPACE_TYPO_CUTOFF):
                existing_map.setdefault("_urls", {})[k] = v
                existing_map[k] = []
                msg = (
                    f"The URL for '{k}' ({v}) is not a known namespace of BattINFO converter. "
                    f"Maybe you meant ({close_match})?"
                )
                _report(msg, errors)
            elif v.endswith(GEN_DELIMS):
                # A namespace of the user's own, with no term list to check against
                existing_map.setdefault("_urls", {})[k] = v
                existing_map.setdefault("_opaque", set()).add(k)
                existing_map[k] = []
                if errors != "ignore":
                    logger.info("'%s' (%s) is a namespace of your own, its terms are not checked.", k, v)
            else:
                # A custom term
                existing_map.setdefault("_terms", set()).add(k)
    elif isinstance(context, list):
        for el in context:
            existing_map = map_context(el, existing_map, errors)
    return existing_map


def get_all_terms(
    obj: list | dict | str | float,
    vocab_terms: set | None = None,
    iri_terms: set | None = None,
    vocab_props: frozenset | set = frozenset(),
    opaque_prefixes: frozenset | set = frozenset(),
) -> tuple[set, set]:
    """Recursive search for all terms in JSON-LD.

    Returns (vocab_terms, iri_terms): keys, @type values, and string values of
    @vocab-typed properties resolve through context term definitions, while @id
    and other string values only expand prefixes.

    Values of predicates in `opaque_prefixes` are left alone: without a term list
    for the namespace there is no way to tell a literal predicate from a node one.
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
                else:
                    # A non-text @id or @type cannot be an IRI
                    logger.warning("'%s' is '%s', which cannot be an IRI", k, v)
            elif not k.startswith("@"):
                vocab_terms.add(k)
                if k not in LITERAL_PREDICATES and k.split(":", 1)[0] not in opaque_prefixes:
                    target = vocab_terms if k in vocab_props else iri_terms
                    if isinstance(v, str):
                        target.add(v)
                    elif isinstance(v, list):
                        for el in v:
                            if isinstance(el, str):
                                target.add(el)
            get_all_terms(v, vocab_terms, iri_terms, vocab_props, opaque_prefixes)
    elif isinstance(obj, list):
        for i in obj:
            get_all_terms(i, vocab_terms, iri_terms, vocab_props, opaque_prefixes)
    return vocab_terms, iri_terms


def check_term_against_context(term: str, mapped_context: dict, *, warn_redundant_prefix: bool = True) -> None:
    """Raise error if term is not in context, or not already IRI."""
    if term.startswith("http"):  # It is already an absolute IRI
        return
    if term in mapped_context.get("_terms", ()):
        return  # defined as its own term in the context
    if ":" in term:  # It is prefixed - check
        prefix, label = term.split(":", 1)
        if prefix in mapped_context.get("_opaque", ()):
            return  # a user's own namespace, no term list to check against
        if prefix not in mapped_context:
            if prefix in mapped_context.get("_declared", {}):
                return  # declared by the remote context, no term list to check against
            if prefix in mapped_context.get("_terms", ()):
                # JSON-LD leaves 'prefix:label' alone unless the prefix maps to an IRI
                # ending in a general delimiter, so this would not expand at all
                msg = (
                    f"'{prefix}' maps to a single term, so '{term}' is not expanded. "
                    f"End its URL in one of {' '.join(GEN_DELIMS)} to use it as a namespace."
                )
                raise ValueError(msg)
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


def term_resolves(term: object, mapped_context: dict) -> bool:
    """Return True if `term` is a term the context can expand."""
    if not isinstance(term, str) or not term:
        return False
    try:
        check_term_against_context(term, mapped_context, warn_redundant_prefix=False)
    except ValueError:
        return False
    return True


def known_terms(mapped_context: dict) -> list[str]:
    """Every term the context can expand, prefixed ones included."""
    terms = list(mapped_context.get("_base", []))
    terms += sorted(mapped_context.get("_terms", ()))
    for prefix, labels in mapped_context.items():
        if not prefix.startswith("_") and isinstance(labels, list):
            terms += [f"{prefix}:{label}" for label in labels]
    return terms


def suggest_terms(term: object, mapped_context: dict, extra: Iterable[str] = (), limit: int = 3) -> list[str]:
    """Close matches for a term that did not resolve, to offer as 'did you mean'.

    Matching ignores case, so a lowercase value still finds its ontology class.
    """
    if not isinstance(term, str) or not term:
        return []
    candidates = {c: c for c in (*known_terms(mapped_context), *extra) if isinstance(c, str)}
    folded = {c.lower(): c for c in candidates}
    matches = get_close_matches(term.lower(), list(folded), n=limit, cutoff=SUGGESTION_CUTOFF)
    return [folded[m] for m in matches]


def did_you_mean(term: object, mapped_context: dict, extra: Iterable[str] = ()) -> str:
    """Build a hint naming the closest terms, empty when there are none."""
    matches = suggest_terms(term, mapped_context, extra)
    if not matches:
        return ""
    named = ", ".join(f"'{m}'" for m in matches)
    return f" Did you mean {named}?"


def validate_jsonld(doc: dict, errors: ErrorMode = "warn") -> None:
    """Check that terms in JSON-LD are known in context."""
    # Map out the context - URL: list of valid terms
    context = doc["@context"]
    mapped_context = map_context(context, errors=errors)

    # Get all the terms in the json-ld
    vocab_props = mapped_context.get("_vocab", frozenset())
    # Prefixes we have no term list for, declared by the remote context or by the user
    opaque_prefixes = (set(mapped_context.get("_declared", {})) - set(mapped_context)) | mapped_context.get(
        "_opaque", set()
    )
    vocab_terms, iri_terms = get_all_terms(doc, vocab_props=vocab_props, opaque_prefixes=opaque_prefixes)
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
            msg = f"{e}{did_you_mean(term, mapped_context)}"
            if errors == "raise":
                raise ValueError(msg) from e
            logger.warning(msg)
