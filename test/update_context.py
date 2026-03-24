"""Script to update the cached mapped terms in a context."""

import json
from pathlib import Path

from pyld.jsonld import JsonLdProcessor

FIXTURE_DIR = Path(__file__).resolve().parent
STANDARD_JSON_PATH = FIXTURE_DIR / "BattINFO_converter_BattINFO_converter_standard_JSON_version_1.1.16.json"


def main() -> None:
    """Update the context file."""
    # Use pyld to process the context and fetch remotes
    doc = json.load(STANDARD_JSON_PATH.open("r"))
    processor = JsonLdProcessor()
    active_ctx = processor.process_context(processor._get_initial_context({}), doc["@context"], {})

    # active_ctx["mappings"] is a dict of term -> {"@id": "<absolute IRI>", ...}
    mapped_terms = sorted(active_ctx.get("mappings", {}).keys())
    with (FIXTURE_DIR / "mapped_terms.json").open("w") as f:
        json.dump(mapped_terms, f, indent=4)


if __name__ == "__main__":
    main()
