"""Function to update the cached mapped terms.

Running this script will update the JSON files in src/battinfoconverter_backend/_context.
It grabs json-ld/ttl/xml from remote and parses them, to find valid terms.
"""

import json
import logging
from pathlib import Path

import requests
from rdflib import Graph
from rdflib.namespace import OWL, RDF, RDFS, Namespace

logger = logging.getLogger(__name__)

QUDT = Namespace("http://qudt.org/schema/qudt/")
UNIT = Namespace("http://qudt.org/vocab/unit/")
RDFS_NS = Namespace("http://www.w3.org/2000/01/rdf-schema#")

CONTEXT_DIR = Path(__file__).parent.parent / "src" / "battinfoconverter_backend" / "_context"

CONTEXT = {
    "emmo": {
        "namespace": "https://w3id.org/emmo#",
        "url": "https://w3id.org/emmo",
        "format": "ttl",
    },
    "echem": {
        "namespace": "https://w3id.org/emmo/domain/electrochemistry#",
        "url": "https://w3id.org/emmo/domain/electrochemistry/context/context",
        "format": "jsonld",
    },
    "schema": {
        "namespace": "https://schema.org/",
        "url": "https://schema.org/version/latest/schemaorg-current-https.jsonld",
        "format": "jsonld",
    },
    "battery": {
        "namespace": "https://w3id.org/emmo/domain/battery#",
        "url": "https://w3id.org/emmo/domain/battery/context/context",
        "format": "jsonld",
    },
    "chemical": {
        "namespace": "https://w3id.org/emmo/domain/chemical-substance#",
        "url": "https://w3id.org/emmo/domain/chemical-substance/context/context",
        "format": "jsonld",
    },
    "unit": {
        "namespace": "https://qudt.org/vocab/unit/",
        "url": "https://qudt.org/vocab/unit/",
        "format": "ttl",
    },
    "rdfs": {
        "namespace": "http://www.w3.org/2000/01/rdf-schema#",
        "url": "https://www.w3.org/2000/01/rdf-schema.ttl",
        "format": "ttl",
    },
}


def update_context_cache() -> None:
    """Update the context file."""
    for name, settings in CONTEXT.items():
        terms = set()

        if settings["format"] == "jsonld":
            data = requests.get(settings["url"], timeout=10).json()

            # For emmo, look in context
            terms = {
                k
                for k, v in data["@context"].items()
                if (not k.startswith("@") and not (isinstance(v, str) and v.endswith(("#", "/"))))
            }
            # For schema, look in graph
            if name == "schema" and "@graph" in data:
                for item in data["@graph"]:
                    if "@id" in item:
                        iri = item["@id"]
                        if iri.startswith("schema:"):
                            term = iri.split(":", 1)[-1]
                            terms.add(term)

        else:
            g = Graph()
            g.parse(settings["url"], format=settings["format"])

            for s in g.subjects(RDF.type, OWL.Class):
                for label in g.objects(s, RDFS.label):
                    if label.language in {"en", None}:
                        terms.add(label.value)

            for s in g.subjects(RDF.type, OWL.ObjectProperty):
                for label in g.objects(s, RDFS.label):
                    if label.language in {"en", None}:
                        terms.add(label.value)

            for s in g.subjects(RDF.type, OWL.DatatypeProperty):
                for label in g.objects(s, RDFS.label):
                    if label.language in {"en", None}:
                        terms.add(label.value)

            for s in g.subjects(RDF.type, QUDT.Unit):
                iri = str(s)
                if iri.startswith(str(UNIT)):
                    term = iri.rsplit("/", 1)[-1]
                    terms.add(term)

            for s in g.subjects(RDF.type, RDFS.Class):
                iri = str(s)
                if iri.startswith(str(RDFS_NS)):
                    term = iri.split("#", 1)[-1]
                    terms.add(term)

            for s in g.subjects(RDF.type, RDF.Property):
                iri = str(s)
                if iri.startswith(str(RDFS_NS)):
                    term = iri.split("#", 1)[-1]
                    terms.add(term)

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
