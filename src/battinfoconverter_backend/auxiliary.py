"""Auxiliary functions for building JSON-LD structures from tabular data."""

import json
import logging
import re
from contextlib import suppress
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

from .registry import Registry, tokenize

logger = logging.getLogger(__name__)

# Regex used to detect multi-connector suffixes such as "hasSolventA"
_MULTI_CONNECTOR_SUFFIX = re.compile(r"^(?P<base>.+?)(?P<suffix>[A-Z])$")

# Predicates allowed literal values (rather than nodes), split by datatype.
# Cached from the ontologies by scripts/update_context.py.
LITERALS_FILE = Path(__file__).parent / "_context" / "literal_predicates.json"
with LITERALS_FILE.open(encoding="utf-8") as _f:
    _literals = json.load(_f)

# These will be coerced into ISO8601
DATE_PREDICATES = set(_literals["date"])

# These are not coerced to strings
NUMBER_PREDICATES = set(_literals["number"])

LITERAL_PREDICATES = set(_literals["string"]) | NUMBER_PREDICATES | DATE_PREDICATES

# The following keys will create an object with @type value, and look up a unique ID in @Classes
# E.g. "schema:manufacturer": "Empa"
# becomes {"@type": "schema:Organisation", "@id": id-lookedup-from-@Classes, "schema:name": "Empa"}
TYPES_WITH_ID = {
    "schema:manufacturer": "schema:Organization",
    "schema:creator": "schema:Person",
}

# Deprecation warning for terms that get put in as comments
COMMENT_WARNING = (
    "DEPRECATION: "
    "'%s' is not understood as an ontology term, adding it as a comment. "
    "Implicit comments will be removed in future versions. "
    "To add comments, put 'rdfs:comment' or 'Comment' at the end of the path."
)


def _select_entry(
    label: str | None,
    entries: list[dict[str, Any]],
    part: str,
    traversed: list[str],
    data_container: Registry,
) -> dict[str, Any] | None:
    """Pick the best existing connector node for an incoming value.

    Selection strategy (in order of preference):
    1. Token-overlap scoring against metadata label.
       The score tuple is (unique_base_hits, unique_hits, subset_flag,
       overlap, -order).
    2. Round-robin via ``next_index`` when no tokens match.
    3. Find any entry whose node does not yet have ``part`` populated.
    4. Check ``get_last`` as a last resort.

    Returns ``None`` if no suitable entry exists (caller should create one).
    """
    if not entries:
        return None

    tokens = set(tokenize(label)) if label else set()

    if tokens:
        # Pre-compute how many entries share each token - rare tokens are
        # more discriminative and get higher weight in the score.
        token_occurrence: dict[str, int] = {}
        base_occurrence: dict[str, int] = {}
        for entry in entries:
            combined = entry.get("base_tokens", set()) | entry.get("alias_tokens", set())
            base_tokens = entry.get("base_tokens", set())
            for t in combined:
                token_occurrence[t] = token_occurrence.get(t, 0) + 1
            for t in base_tokens:
                base_occurrence[t] = base_occurrence.get(t, 0) + 1

        chosen: dict[str, Any] | None = None
        best_score: tuple[int, int, int, int, int] | None = None

        for entry in entries:
            base_tokens = entry.get("base_tokens", set())
            entry_tokens = base_tokens | entry.get("alias_tokens", set())
            if not entry_tokens:
                continue

            overlap = len(tokens & entry_tokens)
            if overlap == 0:
                continue

            # 1. unique_base_hits: tokens that only appear in this entry's
            #    base (not alias) token set -> strongest signal of a direct match.
            unique_base_hits = sum(1 for t in tokens if t in base_tokens and base_occurrence.get(t, 0) == 1)
            # 2. unique_hits: tokens that only appear in one entry overall
            #    (base + alias) -> good discriminator when base tokens tie.
            unique_hits = sum(1 for t in tokens if t in entry_tokens and token_occurrence.get(t, 0) == 1)
            # 3. subset_flag: 1 if the entry's entire token set is covered by
            #    the incoming label tokens (tight match, no extra noise).
            subset_flag = 1 if entry_tokens <= tokens else 0

            score = (unique_base_hits, unique_hits, subset_flag, overlap, -entry["order"])

            if best_score is None or score > best_score:
                best_score = score
                chosen = entry

        if chosen is not None:
            return chosen

    # Fallback 1: round-robin assignment
    path_key = tuple(traversed)
    index = data_container.next_index(path_key)
    if index < len(entries):
        return entries[index]

    # Fallback 2: find an entry whose target slot is still empty
    for entry in entries:
        if entry["node"].get(part) in (None, {}):
            return entry

    # Fallback 3: return the most recently visited entry
    last_key_base = tuple(traversed[:-1])
    for entry in entries:
        connector = entry.get("connector")
        last_key = (*last_key_base, connector)
        if data_container.get_last(last_key) is entry["node"]:
            return entry

    return None


# ===========================================================================
# JSON-LD node mutation helpers
# ===========================================================================


def _merge_type(node: dict[str, Any], new_type: str) -> None:
    """Add ``new_type`` to the ``@type`` field without duplicating it.

    Handles the three possible states of ``@type``:
    - missing -> set directly
    - a single string -> promote to list if different
    - already a list -> append if not present
    """
    if "@type" not in node:
        node["@type"] = new_type
    else:
        existing = node["@type"]
        if isinstance(existing, list):
            if new_type not in existing:
                existing.append(new_type)
        elif existing != new_type:
            node["@type"] = [existing, new_type]


def _add_or_extend_list(node: dict[str, Any], key: str, entry: dict[str, Any]) -> None:
    """Append ``entry`` under ``node[key]``, normalizing to a list when needed.

    - Empty / missing -> store directly (avoids unnecessary single-item lists)
    - Single dict already present -> promote to [existing, entry]
    - Already a list -> append
    """
    current = node.get(key)
    if current in (None, {}):
        node[key] = entry
    elif isinstance(current, list):
        current.append(entry)
    else:
        node[key] = [current, entry]


def _new_item(parent: dict[str, Any], key: str) -> dict[str, Any]:
    """Create a fresh empty dict as a new sibling under ``parent[key]``.

    This is how multi-connector nodes are extended: the first occurrence is
    stored directly, subsequent ones cause promotion to a list.
    """
    value = parent.get(key)
    if value in (None, {}):
        parent[key] = {}
        return parent[key]
    if isinstance(value, list):
        fresh: dict[str, Any] = {}
        value.append(fresh)
        return fresh
    # Single dict already present - promote to list
    parent[key] = [value, {}]
    return parent[key][-1]


def _extract_type(segment: str) -> str:
    """Strip the ``type|`` command prefix if present.

    Path segments like ``type|emmo:Liquid`` carry a type annotation for the
    *measured-property* wrapper.  This helper returns just ``emmo:Liquid``.
    """
    return segment.split("|", 1)[1] if segment.startswith("type|") else segment


# ===========================================================================
# Multi-connector path analysis
# ===========================================================================


def _is_simple_connector(segment: str) -> bool:
    """Return True if ``segment`` looks like a plain camelCase connector.

    Connectors with colons (``emmo:hasProperty``) or underscores are namespace-
    qualified and never have A/B/C suffixes.
    """
    return ":" not in segment and "_" not in segment


def _split_multi_connector(
    part: str,
    multi_connector_candidates: set[str],
) -> tuple[str, int | None]:
    """Detect and strip A/B/C suffixes from multi-connector path segments.

    ``hasSolventA`` -> (``hasSolvent``, 0)
    ``hasSolventB`` -> (``hasSolvent``, 1)
    ``hasStringValue`` -> (``hasStringValue``, None)   ← no suffix stripping

    The suffix is only stripped when the *base* name appears in
    ``multi_connector_candidates`` but the *suffixed* form does not - this
    avoids mis-parsing connectors whose names happen to end in a capital letter.
    """
    match = _MULTI_CONNECTOR_SUFFIX.match(part)
    if match and _is_simple_connector(part):
        base = match.group("base")
        if base in multi_connector_candidates and part not in multi_connector_candidates:
            return base, ord(match.group("suffix")) - ord("A")
    return part, None


# ===========================================================================
# Indexed multi-connector node management
# ===========================================================================


def _ensure_indexed_connector_node(
    parent: dict[str, Any],
    connector: str,
    parent_path: tuple[str, ...],
    index: int,
    metadata: str | None,
    value: str | float | None,
    data_container: Registry,
) -> dict[str, Any]:
    """Return the connector node at position ``index``, creating placeholders as needed.

    If the registry only has 0 entries but we need index 2, this creates
    placeholder nodes at indices 0 and 1 first, then the real node at 2.
    """
    entries = [e for e in data_container.get_entries(parent_path, parent) if e.get("connector") == connector]

    while len(entries) <= index:
        is_target = len(entries) == index
        holder = parent.get(connector)

        # Reuse an existing empty node rather than creating a new sibling,
        # but only if it hasn't already been registered.
        if (
            isinstance(holder, dict)
            and (not holder or list(holder.keys()) == ["@type"])
            and not any(e.get("node") is holder for e in data_container.get_entries(parent_path, parent))
            and len(entries) == 0
        ):
            target_node = holder
        else:
            target_node = _new_item(parent, connector)

        data_container.register(
            parent_path,
            connector,
            target_node,
            metadata if is_target else None,
            value if is_target else None,
            parent,
        )
        entries = [e for e in data_container.get_entries(parent_path, parent) if e.get("connector") == connector]

    return entries[index]["node"]


# ===========================================================================
# Main entry point
# ===========================================================================


def add_to_structure(
    jsonld: dict,
    path: list[str],
    value: str | float | None,
    unit: str,
    data_container: Registry,
    metadata: str | None = None,
) -> None:
    """Insert ``value`` into the JSON-LD structure at the location described by ``path``.

    Args:
        jsonld:
            The JSON-LD document being built (mutated in place).
        path:
            Ordered list of path segments. E.g.
            - A plain connector name, e.g. "hasSolvent"
            - A multi-connector with suffix, e.g. "hasSolventA"
            - A type command, e.g. "type|emmo:Liquid" (sets ``@type``, no traversal)
            - A reverse command, e.g. "rev|isPartOf" (writes under ``@reverse``)
            - An ontology type leaf, e.g. "emmo:MassPercentage" (used in measured-
              property wrappers)
        value:
            The value to store.
        unit:
            Looked up in the "unit_map".
        data_container:
            The Registry object providing data and tracking nodes
        metadata:
            Column label from the schema sheet.

    Returns:
        None - mutates jsonld dict in place.

    """
    # Skip empty / NaN values
    if (
        value is None
        or (isinstance(value, str) and value.strip() == "")
        or (isinstance(value, float) and pd.isna(value))
        or (isinstance(value, (int, float, Decimal)) and pd.isna(pd.Series([value])[0]))
    ):
        return

    # Load lookup tables from the ExcelContainer Registry
    unit_map = data_container.data["unit_map"]
    context_connector = data_container.data["context_connector"]
    connectors = set(context_connector["Item"])
    unique_id_map = data_container.data["unique_id_map"]

    # Walk the path
    current_level = jsonld
    traversed: list[str] = []  # segments successfully visited so far
    logger.debug("'%s': Inserting value '%s' into %s", metadata, value, path)
    for index, parts in enumerate(path):
        logger.debug("Checking %d: %s", index, parts)

        part = parts
        if "|" in parts:
            if parts.startswith("type|"):
                # type| segments annotate the *current* node and are not
                # traversal steps - they do not advance current_level.
                _, typ = parts.split("|", 1)
                logger.debug("It's a type, annotating with '@%s'", typ)
                if typ:
                    _merge_type(current_level, typ)
                    parent_path = tuple(traversed[:-1]) if traversed else ()
                    data_container.update_tokens(parent_path, current_level, typ)
                else:  # Set the type of the current level to the value
                    current_level["@type"] = value
                continue  # Go to the next path part
            if parts.startswith("rev|"):
                _, part = parts.split("|", 1)
                # rev| writes into the @reverse block (back-reference in JSON-LD)
                current_level = current_level.setdefault("@reverse", {})
            else:
                msg = f"Path segment '{parts}' contains special character |, without rev| or"
                raise ValueError(msg)
        if part in {"Comment", "comment"}:
            logger.debug("Treating 'comment' as 'rdfs:comment'")
            part = "rdfs:comment"

        # Strip A/B/C suffix to get the base connector name and its index
        part, connector_index = _split_multi_connector(part, data_container.multi_connector_candidates)

        # Lists can appear when a connector already has multiple nodes;
        # always target the last (most recently created) item.
        if isinstance(current_level, list):
            current_level = current_level[-1]

        last = index == len(path) - 1
        penultimate = index == len(path) - 2
        next_segment = path[index + 1] if index + 1 < len(path) else None

        traversed.append(part)
        parent_path = tuple(traversed[:-1])

        # A segment is a "multi-connector" if its base name is a known
        # multi-connector AND either an explicit suffix index was found OR
        # the next segment is a type| command (which implies this node
        # will have typed siblings).
        is_multi_connector = bool(
            part in data_container.multi_connector_candidates
            and (connector_index is not None or (next_segment and next_segment.startswith("type|")))
        )

        # Ensure the key exists in the current dict
        if part not in current_level and (value or unit):
            if part in connectors:
                connector_type = context_connector.loc[context_connector["Item"] == part, "Key"].to_numpy()[0]
                current_level[part] = {} if pd.isna(connector_type) else {"@type": connector_type}
            else:
                current_level[part] = {}

        next_level = current_level[part]

        # ==============================================================
        # CASE 1 - Measured property
        # ==============================================================
        # When we're at the *penultimate* segment and a unit is present,
        # the final segment is the ontology type of the measurement, not a
        # plain property name.  Wrap the value in the EMMO measured-property
        # structure and stop.
        if penultimate and unit != "No Unit":
            if pd.isna(unit):
                msg = f"Value '{value}' at path '{path}' is missing a required unit."
                raise ValueError(msg)
            if not unit_map.get(unit):
                msg = f"The unit '{unit}' was not found in the @Units tab."
                raise ValueError(msg)
            mp_entry = {
                "@type": _extract_type(path[-1]),
                "hasNumericalPart": {
                    "@type": "RealData",
                    "hasNumberValue": value,
                },
                "hasMeasurementUnit": unit_map[unit],
            }
            parent = current_level[-1] if isinstance(current_level, list) else current_level
            logger.debug(
                "Adding an object with type %s, numerical part %s, measurement unit %s",
                _extract_type(path[-1]),
                value,
                unit_map[unit],
            )
            _add_or_extend_list(parent, part, mp_entry)
            break

        # ==============================================================
        # CASE 2 - Multi-connector traversal (not the final segment)
        # ==============================================================
        # We're at an intermediate multi-connector and need to navigate
        # into the correct child node (creating it if necessary).
        if is_multi_connector and not last:
            logger.debug("Found a multiconnector, need to figure out where it goes")
            connector_parent_path = tuple(traversed[:-1])
            registry_entries = [
                e
                for e in data_container.get_entries(connector_parent_path, current_level)
                if e.get("connector") == part
            ]

            if connector_index is not None:
                logger.debug("Has connector index '%s'", connector_index)
                # Explicit suffix index (hasSolventA -> index 0) - navigate
                # directly to (or create) the node at that index.
                if connector_index < len(registry_entries):
                    target_node = registry_entries[connector_index]["node"]
                else:
                    target_node = _ensure_indexed_connector_node(
                        current_level,
                        part,
                        connector_parent_path,
                        connector_index,
                        metadata,
                        None,
                        data_container,
                    )
                data_container.remember_last(tuple(traversed), target_node)
                data_container.update_tokens(connector_parent_path, target_node, metadata)
                current_level = target_node
                continue

            # No explicit index - use type matching or token scoring to
            # find the right existing node, or create a new one.
            logger.debug("No connector index found, trying to guess where it should go")
            desired_type: str | None = None
            if next_segment and next_segment.startswith("type|"):
                _, desired_type = next_segment.split("|", 1)
                logger.debug("Next node has type %s, will look for that", desired_type)

            # Prefer a node that already has the desired @type
            selected = None
            if desired_type:
                for entry in registry_entries:
                    existing_type = entry["node"].get("@type")
                    types = existing_type if isinstance(existing_type, list) else [existing_type]
                    if desired_type in types:
                        logger.debug("Found an existing node with type '%s'", desired_type)
                        selected = entry
                        break

            if selected is None:
                logger.debug("Could not find existing node with suffix, trying other strategies")
                selected = _select_entry(metadata, registry_entries, part, traversed, data_container)

            # Discard the match if the type doesn't align
            if selected is not None and desired_type:
                existing_type = selected["node"].get("@type")
                types = existing_type if isinstance(existing_type, list) else [existing_type]
                if desired_type not in types:
                    logger.debug("Couldn't find the desired type %s", desired_type)
                    selected = None

            if selected is not None:
                target_node = selected["node"]
            else:
                # No suitable existing node - create one
                entries_for_parent = data_container.get_entries(connector_parent_path, current_level)
                holder = current_level.get(part)
                if (
                    isinstance(holder, dict)
                    and (not holder or list(holder.keys()) == ["@type"])
                    and not any(e.get("node") is holder for e in entries_for_parent)
                ):
                    target_node = holder
                else:
                    target_node = _new_item(current_level, part)

                entries_for_parent = data_container.get_entries(connector_parent_path, current_level)
                if not any(e.get("node") is target_node for e in entries_for_parent):
                    data_container.register(
                        connector_parent_path,
                        part,
                        target_node,
                        metadata,
                        None,
                        current_level,
                    )

            data_container.remember_last(tuple(traversed), target_node)
            data_container.update_tokens(connector_parent_path, target_node, metadata)
            current_level = target_node
            continue

        # ==============================================================
        # CASE 3 - Final value assignment  (unit == "No Unit")
        # ==============================================================
        if last:
            logger.debug("At last section with part '%s'", part)

            # Special case: value transformed to a dict with a @type and @id
            if part in TYPES_WITH_ID:
                logger.debug("Special case - looking up id")

                payload: dict[str, Any] = {
                    "@type": TYPES_WITH_ID[part],
                    "schema:name": value,
                }
                if uid := unique_id_map.get(value):
                    payload["@id"] = uid
                else:
                    logger.warning(
                        "'%s' has value '%s'. This is a '%s' - we recommend adding a unique ID in the @Classes tab.",
                        metadata,
                        value,
                        part,
                    )

                registry_entries = _get_connector_entries_for_parent(
                    parent_path, current_level, data_container, is_multi_connector
                )
                if registry_entries:
                    selected = _select_entry(metadata, registry_entries, part, traversed, data_container)
                    if selected is not None:
                        selected["node"][part] = payload
                        if part in current_level and current_level[part] in (None, {}):
                            current_level.pop(part)
                        data_container.update_tokens(
                            parent_path,
                            selected["node"],
                            metadata,
                            value if isinstance(value, str) else None,
                        )
                        break

                current_level[part] = payload
                break

            # Special case: literal values - no @id lookup needed.
            if part in LITERAL_PREDICATES:
                if part == "rdfs:comment":
                    # Comments also get the key and unit included if they exist
                    prefix = f"{metadata}: " if metadata is not None else ""
                    suffix = f" {unit}" if unit is not None and unit != "No Unit" else ""
                    value = f"{prefix}{value}{suffix}"
                if part in DATE_PREDICATES:
                    value = coerce_date_to_iso(value)
                elif part not in NUMBER_PREDICATES:
                    value = str(value)
                logger.debug("Special case - adding value '%s' to '%s' as a literal", value, part)
                target_node = current_level[-1] if isinstance(current_level, list) else current_level
                if existing_value := target_node.get(part):
                    if isinstance(existing_value, str):
                        target_node[part] = [existing_value, value]
                    elif isinstance(existing_value, list):
                        target_node[part].append(value)
                else:
                    target_node[part] = value
                break

            # General case: ontology node / @id
            registry_entries = _get_connector_entries_for_parent(
                parent_path, current_level, data_container, is_multi_connector
            )

            if registry_entries:
                # Route the value to the best-matching registered node
                selected = _select_entry(metadata, registry_entries, part, traversed, data_container)
                if selected is not None:
                    target = selected["node"]
                    holder = target.get(part)
                    if not isinstance(holder, dict):
                        target[part] = {} if holder in (None, {}) else {"rdfs:comment": holder}
                    target_node = target[part]

                    if value in unique_id_map:
                        # Known ontology term -> link via @id and @type
                        logger.debug("Value '%s' is a known ontology term, linking with @id and @type", value)
                        if uid := unique_id_map.get(value):
                            target_node["@id"] = uid
                        _merge_type(target_node, value)
                    elif value:
                        # Unknown term -> write as a comment but WARN
                        logger.warning(COMMENT_WARNING, value)
                        target_node["rdfs:comment"] = value

                    if part in current_level and current_level[part] in (None, {}):
                        current_level.pop(part)
                    data_container.update_tokens(
                        parent_path,
                        target,
                        metadata,
                        value if isinstance(value, str) else None,
                    )
                    break

            # No registry entry - handle multi-connector leaf or plain write
            if is_multi_connector:
                # Figure out which connector to use
                target_node = _assign_multi_connector_leaf(
                    current_level,
                    part,
                    parent_path,
                    connector_index,
                    metadata,
                    value,
                    data_container,
                )
                data_container.update_tokens(
                    parent_path,
                    target_node,
                    metadata,
                    value if isinstance(value, str) else None,
                )
            else:
                # Just continue on the path
                target_node = next_level

            # Write the value into target_node
            if value in unique_id_map:
                if uid := unique_id_map.get(value):
                    target_node["@id"] = uid
                _merge_type(target_node, value)
            elif value:
                # Legacy behaviour: do not store with metadata, overwrite existing values
                logger.warning(COMMENT_WARNING, value)
                target_node["rdfs:comment"] = value
            break

        # Did not match any of the 3 cases: step into the next level
        current_level = next_level


def _get_connector_entries_for_parent(
    parent_path: tuple[str, ...],
    current_level: dict[str, Any],
    data_container: Registry,
    is_multi_connector: bool,
) -> list[dict[str, Any]]:
    """Return registry entries for the connector that owns the current level.

    For single-valued connectors we look one level up (the *parent* connector
    registered in the registry) so a value like ``hasStringValue`` lands on
    the correct sibling node when multiple siblings exist.

    Returns an empty list for multi-connectors (caller handles those directly).
    """
    if is_multi_connector or not isinstance(current_level, dict):
        return []

    connector_parent_path: tuple[str, ...] = parent_path[:-1]
    connector_key: str | None = parent_path[-1] if parent_path else None
    if not (connector_parent_path and connector_key):
        return []

    return [
        entry
        for entry in data_container.get_entries(connector_parent_path)
        if entry.get("connector") == connector_key and isinstance(entry.get("node"), dict)
    ]


def _assign_multi_connector_leaf(
    current_level: dict[str, Any],
    part: str,
    parent_path: tuple[str, ...],
    connector_index: int | None,
    metadata: str | None,
    value: str | float | None,
    data_container: Registry,
) -> dict[str, Any]:
    """Create or retrieve the target node for a multi-connector *leaf* segment.

    Three sub-cases:

    1. Collapsible + index 0 + not yet registered -> reuse or create a single
       node (no list promotion).  Used when the schema guarantees at most one
       occurrence of this connector.

    2. Explicit suffix index -> delegate to ``_ensure_indexed_connector_node``.

    3. No index -> always create a new sibling node.
    """
    connector_path = (*parent_path, part)
    registry_entries = [e for e in data_container.get_entries(parent_path, current_level) if e.get("connector") == part]

    if (
        connector_index is not None
        and connector_path in (data_container.collapsible_multi_paths or set())
        and connector_index == 0
        and not registry_entries
    ):
        # Collapsible leaf - store as a plain dict, not a list
        holder = current_level.get(part)
        if isinstance(holder, dict):
            target_node = holder
        elif holder in (None, {}):
            current_level[part] = {}
            target_node = current_level[part]
        elif isinstance(holder, list) and holder:
            target_node = holder[0]
            current_level[part] = target_node  # collapse list back to dict
        else:
            current_level[part] = {}
            target_node = current_level[part]
        data_container.register(parent_path, part, target_node, metadata, value, current_level)

    elif connector_index is not None:
        target_node = _ensure_indexed_connector_node(
            current_level,
            part,
            parent_path,
            connector_index,
            metadata,
            value,
            data_container,
        )
    else:
        # No index - always a new sibling
        target_node = _new_item(current_level, part)
        data_container.register(parent_path, part, target_node, metadata, value, current_level)

    data_container.remember_last((*tuple(parent_path), part), target_node)
    return target_node


def coerce_date_to_iso(date: str | datetime) -> str:
    """Coerce a date to ISO8601 format (YYYY-MM-DD)."""
    if isinstance(date, datetime):
        return date.date().isoformat()
    if isinstance(date, str):
        seps = ["-", "/", "."]
        orders = [
            ["%Y", "%m", "%d"],
            ["%d", "%m", "%Y"],
        ]
        formats = [s.join(parts) for s in seps for parts in orders]
        for fmt in formats:
            with suppress(ValueError):
                return datetime.strptime(date.strip(), fmt).date().isoformat()  # noqa: DTZ007
    msg = f"Unable to parse date string: {date!r}. Please use YYYY-MM-DD."
    raise ValueError(msg)
