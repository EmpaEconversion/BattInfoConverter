"""Function to update the cached mapped terms.

Running this script will update the JSON files in src/battinfoconverter_backend/_context.
It grabs json-ld/ttl/xml from remote and parses them, to find valid terms.
"""

import json
import logging
from pathlib import Path

import requests
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, Namespace

logger = logging.getLogger(__name__)

QUDT = Namespace("http://qudt.org/schema/qudt/")
UNIT = Namespace("http://qudt.org/vocab/unit/")
RDFS_NS = Namespace("http://www.w3.org/2000/01/rdf-schema#")

CONTEXT_DIR = Path(__file__).parent.parent / "src" / "battinfoconverter_backend" / "_context"

CONTEXT: dict[str, dict] = {
    "emmo": {
        "namespace": "https://w3id.org/emmo#",
        "url": "https://w3id.org/emmo",
        "format": "ttl",
        "filter_by_namespace": True,
    },
    "echem": {
        "namespace": "https://w3id.org/emmo/domain/electrochemistry#",
        "url": "https://w3id.org/emmo/domain/electrochemistry/context/context",
        "format": "jsonld",
        "filter_by_namespace": True,
    },
    "schema": {
        "namespace": "https://schema.org/",
        "url": "https://schema.org/version/latest/schemaorg-current-https.jsonld",
        "format": "jsonld",
        "filter_by_namespace": True,
    },
    "battery": {
        "namespace": "https://w3id.org/emmo/domain/battery#",
        "url": "https://w3id.org/emmo/domain/battery/context/context",
        "format": "jsonld",
        "filter_by_namespace": False,
    },
    "chemical": {
        "namespace": "https://w3id.org/emmo/domain/chemical-substance#",
        "url": "https://w3id.org/emmo/domain/chemical-substance/context/context",
        "format": "jsonld",
        "filter_by_namespace": True,
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
    },
}


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
