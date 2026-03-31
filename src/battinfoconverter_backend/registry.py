"""Provides Registry class.

The Registry is composed of ExcelContainer data, plus attributes and functions for traversing paths.
"""

import logging
import re
from typing import Any

from battinfoconverter_backend.excel_tools import ExcelContainer

logger = logging.getLogger(__name__)

# Regex used to detect multi-connector suffixes such as "hasSolventA"
_MULTI_CONNECTOR_SUFFIX = re.compile(r"^(?P<base>.+?)(?P<suffix>[A-Z])$")


def _is_simple_connector(segment: str) -> bool:
    """Return True if `segment` looks like a plain camelCase connector.

    Connectors with colons (emmo:hasProperty) or underscores are namespace-
    qualified and never have A/B/C suffixes.
    """
    return ":" not in segment and "_" not in segment


class Registry:
    """Wrapper of ExcelContainer.

    Contains additional attributes and functions for tracking nodes during JSON-LD conversion.
    """

    data: dict

    def __init__(self, excel_container: ExcelContainer) -> None:
        """Initialize, build multi connector candidates."""
        self.data = excel_container.data

        self.last_nodes: dict[tuple[str, ...], dict] = {}
        self.path_counts: dict[tuple[str, ...], int] = {}
        self.connector_registry: dict[tuple[str, ...], list[dict]] = {}

        connector_candidates, collapsible_multi_paths = self._build_multi_connector_candidates()

        self.collapsible_multi_paths = collapsible_multi_paths
        self.multi_connector_candidates = connector_candidates

    def _build_multi_connector_candidates(self) -> tuple[set[str], set[tuple[str, ...]]]:
        """Scan the schema's Ontology link column to discover multi-connector bases.

        Returns:
            multi_connector_candidates
                All connector names that may have A/B/C suffixed siblings.
            collapsible_multi_paths
                Paths whose multi-connector is a *leaf* (no children beyond it) and
                can therefore be collapsed to a single node rather than a list.

        """
        context_connector = self.data["context_connector"]
        connectors = set(context_connector["Item"])

        context_toplevel = self.data.get("context_toplevel")
        top_level_connectors = set(context_toplevel["Item"]) if context_toplevel is not None else set()

        multi_connector_candidates = connectors | top_level_connectors | {"Comment"}

        if self.data["schema"] is None or "Ontology link" not in self.data["schema"]:
            return multi_connector_candidates, set()

        multi_paths_with_children: set[tuple[str, ...]] = set()
        multi_paths_seen: set[tuple[str, ...]] = set()

        for link in self.data["schema"]["Ontology link"]:
            if not isinstance(link, str) or link in ("NotOntologize", "Comment"):
                continue

            # Walk each segment of the dash-separated ontology path
            connectors_in_link: list[str] = []
            for raw in link.split("-"):
                if raw.startswith("type|"):
                    continue
                if "|" in raw:
                    command, remainder = raw.split("|", 1)
                    if command == "rev":
                        raw = remainder
                    else:
                        continue
                connectors_in_link.append(raw)

            # Normalise suffixed segments (hasSolventA -> hasSolvent) and track
            # whether they appear mid-path (have children) or only at the end.
            normalized: list[str] = []
            for idx, segment in enumerate(connectors_in_link):
                segment_base = segment
                match = _MULTI_CONNECTOR_SUFFIX.match(segment)
                if match and _is_simple_connector(segment):
                    base = match.group("base")
                    if base.startswith("has"):
                        segment_base = base
                        path_key = (*normalized, segment_base)
                        multi_paths_seen.add(path_key)
                        if idx < len(connectors_in_link) - 1:
                            multi_paths_with_children.add(path_key)
                        multi_connector_candidates.add(base)
                normalized.append(segment_base)

        collapsible = multi_paths_seen - multi_paths_with_children
        logger.debug("Found multi connector candidates %s", multi_connector_candidates)
        logger.debug("Found  collapsible multi paths: %s", collapsible)
        return multi_connector_candidates, collapsible

    # Entry registration
    def register(
        self,
        parent_path: tuple[str, ...],
        connector: str,
        node: dict[str, Any],
        metadata_label: str | None,
        value: Any,
        parent_node: dict[str, Any] | None = None,
    ) -> None:
        """Record a new connector node so future calls can find it.

        `base_tokens` are seeded from `metadata_label` and `value` so
        `_select_entry` can match incoming metadata against the right node.
        """
        entries = self.connector_registry.setdefault(_registry_key(parent_path), [])

        tokens: set[str] = set()
        if metadata_label:
            tokens.update(tokenize(metadata_label))
        if isinstance(value, str):
            tokens.update(tokenize(value))

        entries.append(
            {
                "connector": connector,
                "node": node,
                "base_tokens": tokens,
                "alias_tokens": set(),  # extended later as more values arrive
                "order": len(entries),  # insertion order, used as tie-breaker
                "parent_id": id(parent_node) if parent_node is not None else None,
            }
        )

    def get_entries(
        self,
        parent_path: tuple[str, ...],
        parent_node: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Return all registered entries for `parent_path`.

        If `parent_node` is provided only entries whose `parent_id` matches
        are returned - this handles cases where the same connector path exists
        under multiple distinct parent nodes.
        """
        entries = self.connector_registry.get(_registry_key(parent_path), [])
        if parent_node is None:
            return entries
        parent_id = id(parent_node)
        return [e for e in entries if e.get("parent_id") == parent_id]

    def update_tokens(
        self,
        parent_path: tuple[str, ...],
        node: dict[str, Any],
        *labels: str | None,
    ) -> None:
        """Extend the alias token set for an already-registered entry.

        Called whenever a new value or metadata label arrives for a node that
        was registered earlier, so future `_select_entry` calls have more
        signal to work with.
        """
        entries = self.get_entries(parent_path)
        for entry in entries:
            if entry["node"] is node:
                alias_tokens = entry.setdefault("alias_tokens", set())
                for label in labels:
                    if isinstance(label, str) and label:
                        alias_tokens.update(tokenize(label))
                break

    def remember_last(self, path_key: tuple[str, ...], node: dict[str, Any]) -> None:
        """Store the last node from path."""
        if path_key:
            self.last_nodes[path_key] = node

    def get_last(self, path_key: tuple[str, ...]) -> dict[str, Any] | None:
        """Get the last node from path."""
        return self.last_nodes.get(path_key)

    # Round-robin counter (fallback when token matching fails entirely)
    def next_index(self, path_key: tuple[str, ...]) -> int:
        """Return and increment the assignment counter for `path_key`."""
        counters = self.path_counts
        idx = counters.get(path_key, 0)
        counters[path_key] = idx + 1
        return idx


def tokenize(label: str) -> tuple[str, ...]:
    """Split a label into lowercase alphanumeric tokens for fuzzy matching.

    Example: "hasSolventA" -> ("hassolvent", "a") - but in practice labels
    come from metadata columns like "Solvent A" -> ("solvent", "a").
    """
    return tuple(re.findall(r"[A-Za-z0-9]+", label.lower()))


def is_simple_connector(segment: str) -> bool:
    """Return True if `segment` looks like a plain camelCase connector.

    Connectors with colons (`emmo:hasProperty`) or underscores are namespace-
    qualified and never have A/B/C suffixes.
    """
    return ":" not in segment and "_" not in segment


def _registry_key(parent_path: tuple[str, ...]) -> tuple[str, ...]:
    """Return __root__ if empty.

    Top-level connectors have an empty parent_path; store them under a
    sentinel key so dict lookups are always consistent.
    """
    return parent_path or ("__root__",)
