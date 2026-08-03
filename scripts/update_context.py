"""Function to update the cached mapped terms.

Running this script will update the JSON files in src/battinfoconverter_backend/_context.
It grabs json-ld/ttl/xml from remote and parses them, to find valid terms.
"""

import json
import logging
from pathlib import Path

import requests
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, XSD, Namespace

logger = logging.getLogger(__name__)

QUDT = Namespace("http://qudt.org/schema/qudt/")
UNIT = Namespace("http://qudt.org/vocab/unit/")
RDFS_NS = Namespace("http://www.w3.org/2000/01/rdf-schema#")

CONTEXT_DIR = Path(__file__).parent.parent / "src" / "battinfoconverter_backend" / "_context"
LITERALS_FILE = CONTEXT_DIR / "literal_predicates.json"

CONTEXT: dict[str, dict] = {
    "emmo": {
        "namespace": "https://w3id.org/emmo#",
        "url": "https://w3id.org/emmo",
        "format": "ttl",
        "filter_by_namespace": True,
        "literals": "owl",
    },
    "echem": {
        "namespace": "https://w3id.org/emmo/domain/electrochemistry#",
        "url": "https://w3id.org/emmo/domain/electrochemistry/context/context",
        "format": "jsonld",
        "filter_by_namespace": True,
        "literals": "owl",
        "ontology_url": "https://w3id.org/emmo/domain/electrochemistry",
    },
    "schema": {
        "namespace": "https://schema.org/",
        "url": "https://schema.org/version/latest/schemaorg-current-https.jsonld",
        "format": "jsonld",
        "filter_by_namespace": True,
        "literals": "schema",
        "prefix": "schema:",
    },
    "battery": {
        "namespace": "https://w3id.org/emmo/domain/battery#",
        "url": "https://w3id.org/emmo/domain/battery/context/context",
        "format": "jsonld",
        "filter_by_namespace": False,
        "literals": "owl",
        "ontology_url": "https://w3id.org/emmo/domain/battery",
    },
    "chemical": {
        "namespace": "https://w3id.org/emmo/domain/chemical-substance#",
        "url": "https://w3id.org/emmo/domain/chemical-substance/context/context",
        "format": "jsonld",
        "filter_by_namespace": True,
        "literals": "owl",
        "ontology_url": "https://w3id.org/emmo/domain/chemical-substance",
    },
    "unit": {
        "namespace": "https://qudt.org/vocab/unit/",
        "url": "https://qudt.org/vocab/unit/",
        "format": "ttl",
        "filter_by_namespace": True,
    },
    "rdfs": {
        "namespace": "http://www.w3.org/2000/01/rdf-schema#",
        "url": "https://www.w3.org/2000/01/rdf-schema.ttl",
        "format": "ttl",
        "filter_by_namespace": True,
        "literals": "owl",
        "bare_literals": False,
    },
}

# Literal predicates are cached both bare and prefixed (e.g. "elucidation" and
# "emmo:elucidation"); the prefix is chosen by the namespace of the term's IRI
LITERAL_NS_PREFIXES = {
    CONTEXT[name]["namespace"]: f"{name}:" for name in ("emmo", "echem", "battery", "chemical", "rdfs")
}

NUMBER_RANGES = {
    str(XSD[t])
    for t in (
        "integer",
        "int",
        "long",
        "short",
        "byte",
        "decimal",
        "double",
        "float",
        "nonNegativeInteger",
        "nonPositiveInteger",
        "negativeInteger",
        "positiveInteger",
        "unsignedInt",
        "unsignedLong",
        "unsignedShort",
        "unsignedByte",
    )
}
DATE_RANGES = {str(XSD.date), str(XSD.dateTime)}

# schema.org types whose values are literals; Date/Number subsets get their own kind
SCHEMA_LITERAL_TYPES = {
    "Text",
    "URL",
    "XPathType",
    "CssSelectorType",
    "PronounceableText",
    "Number",
    "Integer",
    "Float",
    "Boolean",
    "Date",
    "DateTime",
    "Time",
}
SCHEMA_DATE_TYPES = {"Date", "DateTime"}
SCHEMA_NUMBER_TYPES = {"Number", "Integer", "Float"}

# Only take schema.org properties applicable (via schema:domainIncludes) to these classes,
# to keep out the hundreds of literal properties irrelevant to battery data
SCHEMA_DOMAIN_WHITELIST = {
    "Thing",
    "CreativeWork",
    "Dataset",
    "MediaObject",
    "Product",
    "IndividualProduct",
    "Organization",
    "Person",
    "SoftwareApplication",
    "SoftwareSourceCode",
    "ChemicalSubstance",
    "MolecularEntity",
    "Intangible",
}

# Predicates whose ontology declaration lacks an rdfs:range
LITERAL_KIND_OVERRIDES = {"hasNumberValue": "number"}


def _terms_from_jsonld(data: dict, namespace_filter: str | None) -> set:
    """Get set of terms from jsonld, optionally matching the namespace."""
    context = data["@context"]
    prefixes = {k: v for k, v in context.items() if isinstance(v, str) and v.endswith(("#", "/"))}
    terms = set()
    for k, v in context.items():
        if k.startswith("@"):
            continue
        if isinstance(v, str) and v.endswith(("#", "/")):
            continue
        if isinstance(v, str):
            iri = v
        elif isinstance(v, dict) and "@id" in v:
            iri = v["@id"]
        else:
            continue
        if ":" in iri and not iri.startswith("http"):
            prefix, local = iri.split(":", 1)
            if prefix in prefixes:
                iri = prefixes[prefix] + local
        if namespace_filter and not iri.startswith(namespace_filter):
            continue
        terms.add(k)
    return terms


def _owl_labels(g: Graph, rdf_type: URIRef, namespace_filter: str | None) -> set:
    """Return set of matching terms from a graph."""
    terms = set()
    for s in g.subjects(RDF.type, rdf_type):
        if namespace_filter and not str(s).startswith(namespace_filter):
            continue
        for label in g.objects(s, RDFS.label):
            if isinstance(label, Literal) and label.language in {"en", None}:
                terms.add(label.value)
    return terms


def _terms_from_ttl(url: str, namespace_filter: str | None) -> set:
    """Get set terms from ttl from ttl."""
    g = Graph()
    g.parse(url, format="ttl")
    terms: set = set()
    for rdf_type in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty):
        terms |= _owl_labels(g, rdf_type, namespace_filter)
    for s in g.subjects(RDF.type, QUDT.Unit):
        iri = str(s)
        if iri.startswith(str(UNIT)):
            terms.add(iri.rsplit("/", 1)[-1])
    for s in g.subjects(RDF.type, RDFS.Class):
        iri = str(s)
        if iri.startswith(str(RDFS_NS)):
            terms.add(iri.split("#", 1)[-1])
    for s in g.subjects(RDF.type, RDF.Property):
        iri = str(s)
        if iri.startswith(str(RDFS_NS)):
            terms.add(iri.split("#", 1)[-1])
    return terms


def _expand_context_iri(iri: str, prefixes: dict[str, str]) -> str:
    """Expand a prefixed IRI like ``emmo:xyz`` using the context's prefix map."""
    if ":" in iri and not iri.startswith("http"):
        prefix, local = iri.split(":", 1)
        if prefix in prefixes:
            return prefixes[prefix] + local
    return iri


def _literal_predicates_from_owl(g: Graph) -> list[tuple[str, str, str]]:
    """Find literal-valued predicates in an OWL/RDFS graph.

    Returns (iri, label, kind) tuples where kind is "string", "number" or "date".
    """
    found: list[tuple[str, str, str]] = []
    candidates = set(g.subjects(RDF.type, OWL.DatatypeProperty))
    candidates |= set(g.subjects(RDF.type, OWL.AnnotationProperty))
    candidates |= {s for s in g.subjects(RDF.type, RDF.Property) if (s, RDFS.range, RDFS.Literal) in g}
    for s in candidates:
        if (s, RDF.type, OWL.ObjectProperty) in g:
            continue
        ranges = list(g.objects(s, RDFS.range))
        # Some domain ontologies mistype object properties as datatype properties
        if any((r, RDF.type, OWL.Class) in g for r in ranges):
            continue
        range_iris = {str(r) for r in ranges}
        kind = "string"
        if range_iris & NUMBER_RANGES:
            kind = "number"
        elif range_iris & DATE_RANGES:
            kind = "date"
        for label in g.objects(s, RDFS.label):
            if isinstance(label, Literal) and label.language in {"en", None}:
                term_kind = LITERAL_KIND_OVERRIDES.get(str(label.value), kind)
                found.append((str(s), str(label.value), term_kind))
    return found


def _literal_predicates_from_schema(data: dict, prefix: str) -> dict[str, str]:
    """Find literal-valued properties in the schema.org jsonld graph via rangeIncludes."""
    kinds: dict[str, str] = {}
    for item in data.get("@graph", []):
        types = item.get("@type", [])
        if isinstance(types, str):
            types = [types]
        if "rdf:Property" not in types or not item.get("@id", "").startswith("schema:"):
            continue
        domains = item.get("schema:domainIncludes", [])
        if isinstance(domains, dict):
            domains = [domains]
        domain_names = {d["@id"].split(":", 1)[-1] for d in domains if isinstance(d, dict) and "@id" in d}
        if not domain_names & SCHEMA_DOMAIN_WHITELIST:
            continue
        ranges = item.get("schema:rangeIncludes", [])
        if isinstance(ranges, dict):
            ranges = [ranges]
        range_names = {r["@id"].split(":", 1)[-1] for r in ranges if isinstance(r, dict) and "@id" in r}
        literal_ranges = range_names & SCHEMA_LITERAL_TYPES
        if not literal_ranges:
            continue
        kind = "string"
        if literal_ranges <= SCHEMA_DATE_TYPES:
            kind = "date"
        elif literal_ranges <= SCHEMA_NUMBER_TYPES:
            kind = "number"
        kinds[prefix + item["@id"].split(":", 1)[-1]] = kind
    return kinds


def _aliases_from_context(context: dict, iri_kinds: dict[str, str], prefix: str = "") -> dict[str, str]:
    """Find context terms that are aliases of known literal-predicate IRIs."""
    prefixes = {k: v for k, v in context.items() if isinstance(v, str) and v.endswith(("#", "/"))}
    found = {}
    for k, v in context.items():
        if k.startswith("@") or (isinstance(v, str) and v.endswith(("#", "/"))):
            continue
        if isinstance(v, str):
            iri = v
        elif isinstance(v, dict) and "@id" in v:
            iri = v["@id"]
        else:
            continue
        iri = _expand_context_iri(iri, prefixes)
        if iri in iri_kinds:
            found[prefix + k] = iri_kinds[iri]
    return found


def _merge_kinds(target: dict[str, str], new: dict[str, str]) -> None:
    """Merge term kinds, preferring a specific kind (number/date) over "string"."""
    for term, kind in new.items():
        if target.get(term, "string") == "string":
            target[term] = kind


def update_literal_predicates() -> None:
    """Detect predicates taking literal values and cache them split by datatype."""
    term_kinds: dict[str, str] = {}
    iri_kinds: dict[str, str] = {}
    contexts: list[tuple[dict, str]] = []
    for name, settings in CONTEXT.items():
        literals = settings.get("literals")
        prefix = settings.get("prefix", "")
        data: dict = {}
        if settings["format"] == "jsonld":
            data = requests.get(settings["url"], timeout=30).json()
            if "@context" in data:
                contexts.append((data["@context"], prefix))
        if literals == "owl":
            g = Graph()
            g.parse(settings.get("ontology_url", settings["url"]), format="ttl")
            entries = _literal_predicates_from_owl(g)
            for iri, label, kind in entries:
                if settings.get("bare_literals", True):
                    _merge_kinds(term_kinds, {label: kind})
                ns_prefix = next((p for ns, p in LITERAL_NS_PREFIXES.items() if iri.startswith(ns)), None)
                if ns_prefix:
                    _merge_kinds(term_kinds, {ns_prefix + label: kind})
                _merge_kinds(iri_kinds, {iri: kind})
            logger.critical("%s: Found %d literal predicates", name, len(entries))
        elif literals == "schema":
            by_term = _literal_predicates_from_schema(data, prefix)
            _merge_kinds(term_kinds, by_term)
            logger.critical("%s: Found %d literal predicates", name, len(by_term))
    # Context terms aliasing a literal predicate (e.g. hasNumericalValue -> hasNumberValue)
    for context, prefix in contexts:
        _merge_kinds(term_kinds, _aliases_from_context(context, iri_kinds, prefix))
    out = {kind: sorted(t for t, k in term_kinds.items() if k == kind) for kind in ("string", "number", "date")}
    with LITERALS_FILE.open("w") as f:
        json.dump(out, f, indent=0)
    logger.critical(
        "Cached %d string, %d number, %d date literal predicates at %s",
        len(out["string"]),
        len(out["number"]),
        len(out["date"]),
        LITERALS_FILE,
    )


def update_context_cache() -> None:
    """Update the context file."""
    for name, settings in CONTEXT.items():
        namespace_filter = settings.get("namespace") if settings.get("filter_by_namespace", False) else None
        if settings["format"] == "jsonld":
            data = requests.get(settings["url"], timeout=10).json()
            terms = _terms_from_jsonld(data, namespace_filter)

            if name == "schema" and "@graph" in data:
                for item in data["@graph"]:
                    if "@id" in item and item["@id"].startswith("schema:"):
                        terms.add(item["@id"].split(":", 1)[-1])

        elif settings["format"] == "ttl":
            terms = _terms_from_ttl(settings["url"], namespace_filter)

        else:
            logger.critical("Format %s not understood.", settings["format"])
            continue
        term_list = sorted(terms)
        if term_list:
            filepath = CONTEXT_DIR / f"{name}.json"
            with filepath.open("w") as f:
                json.dump({settings["namespace"]: term_list}, f, indent=0)
            logger.critical("%s: Cached %d terms at %s", name, len(term_list), filepath)
        else:
            logger.critical("%s: Failed to find any terms from %s", name, settings["url"])


if __name__ == "__main__":
    update_context_cache()
    update_literal_predicates()
