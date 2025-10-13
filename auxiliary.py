import inspect
import re
import traceback
from decimal import Decimal
from typing import Any, Optional

import pandas as pd

DEBUG_STATUS = False 

def add_to_structure(
    jsonld: dict,
    path: list[str],
    value: Any,
    unit: str,
    data_container: "json_convert.ExcelContainer",
    metadata: str | None = None,
) -> None:
    """
    Adds a value to a JSON-LD structure at a specified path, incorporating units and other contextual information.

        This function processes a path to traverse or modify the JSON-LD structure and handles special cases like 
        measured properties, ontology links, and unique identifiers. It uses data from the provided ExcelContainer 
        to resolve unit mappings and context connectors.

        Args:
            jsonld (dict): The JSON-LD structure to modify.
            path (list[str]): A list of strings representing the hierarchical path in the JSON-LD where the value should be added.
            value (any): The value to be inserted at the specified path.
            unit (str): The unit associated with the value. If 'No Unit', the value is treated as unitless.
            data_container (ExcelContainer): An instance of the ExcelContainer dataclass (from son_convert module) containing supporting data
                                            for unit mappings, connectors, and unique identifiers.
            metadata (str | None): Optional metadata label from the schema sheet, used to align repeated connector entries.
        Returns:
            None: This function modifies the JSON-LD structure in place.

        Raises:
            ValueError: If the value is invalid, a required unit is missing, or an error occurs during path processing.
            RuntimeError: If any unexpected error arises while processing the value and path.
    """
    from json_convert import get_information_value

    # ------------------------------------------------------------------ #
    # helper functions                                                   #
    # ------------------------------------------------------------------ #
    MULTI_CONNECTORS = {
        "hasConstituent",
        "hasAdditive",
        "hasSolute",
        "hasSolvent",
    }

    def _merge_type(node: dict, new_type: str) -> None:
        if "@type" not in node:
            plf(new_type, "_merge_type_not_in", node); node["@type"] = new_type
        else:
            plf(new_type, "_merge_type_exists", node)
            ex = node["@type"]
            if isinstance(ex, list):
                plf(new_type, "_merge_type_list", node)
                if new_type not in ex:
                    plf(new_type, "_merge_type_list_append", node); ex.append(new_type)
            elif ex != new_type:
                plf(new_type, "_merge_type_diff", node); node["@type"] = [ex, new_type]

    def _add_or_extend_list(node: dict, key: str, entry: dict) -> None:
        cur = node.get(key)
        if cur in (None, {}):
            plf(entry, "_add_or_extend_list_new", node); node[key] = entry
        elif isinstance(cur, list):
            plf(entry, "_add_or_extend_list_append", node); cur.append(entry)
        else:
            plf(entry, "_add_or_extend_list_create_list", node); node[key] = [cur, entry]

    def _extract_type(seg: str) -> str:
        return seg.split("|", 1)[1] if seg.startswith("type|") else seg

    def _new_item(parent: dict, key: str) -> dict:
        val = parent.get(key)
        if val in (None, {}):
            plf(key, "_new_item_create", parent); parent[key] = {}
            return parent[key]
        if isinstance(val, list):
            plf(key, "_new_item_append", parent); fresh = {}
            val.append(fresh)
            return fresh
        plf(key, "_new_item_convert_list", parent); parent[key] = [val, {}]
        return parent[key][-1]

    def _register_last(path_key: tuple[str, ...], node: dict) -> None:
        if not path_key:
            plf(path_key, "_register_last_skip", node); return
        history = getattr(data_container, "_last_nodes", None)
        if history is None:
            plf(path_key, "_register_last_init", node); history = {}
            setattr(data_container, "_last_nodes", history)
        history[path_key] = node

    def _get_last(path_key: tuple[str, ...]) -> dict | None:
        history = getattr(data_container, "_last_nodes", None)
        if not history:
            plf(path_key, "_get_last_empty", None); return None
        return history.get(path_key)

    def _next_index(path_key: tuple[str, ...]) -> int:
        counters = getattr(data_container, "_path_counts", None)
        if counters is None:
            plf(path_key, "_next_index_init", None); counters = {}
            setattr(data_container, "_path_counts", counters)
        val = counters.get(path_key, 0)
        counters[path_key] = val + 1
        return val

    def _tokenize(label: str) -> tuple[str, ...]:
        return tuple(re.findall(r"[A-Za-z0-9]+", label.lower()))

    def _registry() -> dict[tuple[str, ...], list[dict]]:
        reg = getattr(data_container, "_connector_registry", None)
        if reg is None:
            plf("registry", "_registry_init", None); reg = {}
            setattr(data_container, "_connector_registry", reg)
        return reg

    def _register_connector_entry(
        parent_path: tuple[str, ...],
        connector: str,
        node: dict,
        metadata_label: str | None,
        value: Any,
    ) -> None:
        reg = _registry()
        entries = reg.setdefault(parent_path, [])
        tokens: set[str] = set()
        if metadata_label:
            plf(metadata_label, "_register_connector_entry_metadata", node); tokens.update(_tokenize(metadata_label))
        if isinstance(value, str):
            plf(value, "_register_connector_entry_value", node); tokens.update(_tokenize(value))
        entries.append(
            {
                "connector": connector,
                "node": node,
                "base_tokens": tokens,
                "alias_tokens": set(),
                "order": len(entries),
            }
        )

    def _update_entry_tokens(
        parent_path: tuple[str, ...], node: dict, *labels: str | None
    ) -> None:
        reg = getattr(data_container, "_connector_registry", None)
        if not reg:
            plf(parent_path, "_update_entry_tokens_no_reg", None); return
        entries = reg.get(parent_path)
        if not entries:
            plf(parent_path, "_update_entry_tokens_no_entries", None); return
        for entry in entries:
            if entry["node"] is node:
                plf(parent_path, "_update_entry_tokens_match", node); alias = entry.setdefault("alias_tokens", set())
                for label in labels:
                    if isinstance(label, str) and label:
                        plf(label, "_update_entry_tokens_label", node); alias.update(_tokenize(label))
                break

    def _get_registry_entries(
        parent_path: tuple[str, ...]
    ) -> list[dict]:
        reg = getattr(data_container, "_connector_registry", None)
        if not reg:
            plf(parent_path, "_get_registry_entries_no_reg", None); return []
        return reg.get(parent_path, [])

    def _select_entry(
        label: str | None,
        entries: list[dict],
        part: str,
        traversed: list[str],
    ) -> dict | None:
        if not entries:
            plf(label, "_select_entry_no_entries", None); return None
        chosen: dict | None = None
        best_score: tuple[int, int, int, int] | None = None
        tokens = set(_tokenize(label)) if label else set()
        token_occurrence: dict[str, int] = {}
        base_occurrence: dict[str, int] = {}
        if tokens:
            plf(tokens, "_select_entry_tokens", None)
            for entry in entries:
                combined = entry.get("base_tokens", set()) | entry.get("alias_tokens", set())
                base = entry.get("base_tokens", set())
                for token in combined:
                    token_occurrence[token] = token_occurrence.get(token, 0) + 1
                for token in base:
                    base_occurrence[token] = base_occurrence.get(token, 0) + 1
        if tokens:
            plf(tokens, "_select_entry_scoring", None)
            for entry in entries:
                base_tokens = entry.get("base_tokens", set())
                entry_tokens = base_tokens | entry.get("alias_tokens", set())
                if not entry_tokens:
                    plf(entry, "_select_entry_no_entry_tokens", None); continue
                overlap = len(tokens & entry_tokens)
                if overlap == 0:
                    plf(entry, "_select_entry_no_overlap", None); continue
                subset_flag = 1 if entry_tokens <= tokens else 0
                unique_base_hits = sum(
                    1
                    for token in tokens
                    if token in base_tokens and base_occurrence.get(token, 0) == 1
                )
                unique_hits = sum(
                    1
                    for token in tokens
                    if token in entry_tokens and token_occurrence.get(token, 0) == 1
                )
                score = (
                    unique_base_hits,
                    unique_hits,
                    subset_flag,
                    overlap,
                    -entry["order"],
                )
                if best_score is None or score > best_score:
                    plf(score, "_select_entry_new_best", entry)
                    best_score = score
                    chosen = entry
        if chosen is not None:
            plf(chosen, "_select_entry_chosen", None); return chosen

        path_key = tuple(traversed)
        idx = _next_index(path_key)
        if idx < len(entries):
            plf(entries[idx], "_select_entry_index", None); return entries[idx]

        for entry in entries:
            existing = entry["node"].get(part)
            if existing in (None, {}):
                plf(entry, "_select_entry_empty_existing", None); return entry

        last_key_base = tuple(traversed[:-1])
        for entry in entries:
            connector = entry.get("connector")
            last_key = last_key_base + (connector,)
            remembered = _get_last(last_key)
            if remembered is entry["node"]:
                plf(entry, "_select_entry_remembered", None); return entry
        return None

    # ------------------------------------------------------------------ #
    # main body                                                          #
    # ------------------------------------------------------------------ #
    try:
        cl = jsonld
        unit_map = (
            data_container.data["unit_map"].set_index("Item").to_dict("index")
        )
        ctx_conn = data_container.data["context_connector"]
        connectors = set(ctx_conn["Item"])
        unique_id = data_container.data["unique_id"]

        # ---- skip only true empties (0 and 0.0 are valid) ------------- #
        if (
            value is None
            or (isinstance(value, str) and value.strip() == "")
            or (isinstance(value, float) and pd.isna(value))
            or (
                isinstance(value, (int, float, Decimal))
                and pd.isna(pd.Series([value])[0])
            )
        ):
            plf(value, "skip_empty", cl); return
        # ---------------------------------------------------------------- #

        traversed: list[str] = []

        for idx, parts in enumerate(path):
            # ---------- special-command parsing ------------------------- #
            if "|" not in parts:
                plf(parts, "no_pipe", cl); part = parts
            elif "type|" in parts:
                plf(parts, "type_command", cl); _, typ = parts.split("|", 1)
                if typ:
                    plf(typ, "type_command_typ", cl); _merge_type(cl, typ)
                continue
            else:  # rev|
                plf(parts, "other_command", cl); cmd, part = parts.split("|", 1)
                if cmd == "rev":
                    plf(cmd, "rev_command", cl); cl = cl.setdefault("@reverse", {})
                else:
                    plf(cmd, "unknown_command", cl); raise ValueError(f"Unknown command {cmd} in {parts}")

            if isinstance(cl, list):
                plf(cl, "list_to_dict", cl); cl = cl[-1]

            last  = idx == len(path) - 1
            penul = idx == len(path) - 2

            traversed.append(part)

            # -------- create node if missing ---------------------------- #
            if part not in cl and (value or unit):
                if part in connectors:
                    plf(part, "create_connector", cl); ctype = ctx_conn.loc[ctx_conn["Item"] == part, "Key"].values[0]
                    cl[part] = {} if pd.isna(ctype) else {"@type": ctype}
                else:
                    plf(part, "create_plain", cl); cl[part] = {}

            nxt = cl[part]

            # -------- measured-property block --------------------------- #
            if penul and unit != "No Unit":
                plf(unit, "penultimate_with_unit", cl)
                if pd.isna(unit):
                    plf(unit, "missing_unit", cl); raise ValueError(f"Value '{value}' missing unit.")
                unit_info = unit_map.get(unit, {})
                mp_entry = {
                    "@type": _extract_type(path[-1]),
                    "hasNumericalPart": {
                        "@type": "emmo:RealData",
                        "hasNumberValue": value,
                    },
                    "hasMeasurementUnit": unit_info.get("Key", "UnknownUnit"),
                }
                parent = cl[-1] if isinstance(cl, list) else cl
                plf(parent, "measured_property", parent); _add_or_extend_list(parent, part, mp_entry)
                break

            # -------- final-value branch -------------------------------- #
            if last and unit == "No Unit":
                plf(value, "final_value_branch", cl); parent_path = tuple(traversed[:-1])

                registry_entries = []
                if part not in MULTI_CONNECTORS and isinstance(cl, dict):
                    plf(part, "final_value_non_multi", cl)
                    for entry in _get_registry_entries(parent_path):
                        node = entry.get("node")
                        if isinstance(node, dict):
                            plf(node, "final_value_registry_entry", cl); registry_entries.append(entry)

                if registry_entries:
                    plf(registry_entries, "final_value_has_registry", cl); selected = _select_entry(metadata, registry_entries, part, traversed)
                    if selected is not None:
                        plf(selected, "final_value_selected", cl); target = selected["node"]
                        holder = target.get(part)
                        if not isinstance(holder, dict):
                            plf(holder, "final_value_holder_not_dict", target); target[part] = (
                                {} if holder in (None, {}) else {"rdfs:comment": holder}
                            )
                        tgt = target[part]
                        if value in unique_id["Item"].values:
                            plf(value, "final_value_unique_id", tgt); uid = get_information_value(
                                df=unique_id,
                                row_to_look=value,
                                col_to_look="ID",
                                col_to_match="Item",
                            )
                            if not pd.isna(uid):
                                plf(uid, "final_value_set_id", tgt); tgt["@id"] = uid
                            _merge_type(tgt, value)
                        elif value:
                            plf(value, "final_value_comment", tgt); tgt["rdfs:comment"] = value
                        if part in cl and cl[part] in (None, {}):
                            plf(part, "final_value_cleanup", cl); cl.pop(part)
                        _update_entry_tokens(
                            parent_path,
                            target,
                            metadata,
                            value if isinstance(value, str) else None,
                        )
                        break

                if part in MULTI_CONNECTORS:
                    plf(part, "final_value_multi_connector", cl); tgt = _new_item(cl, part)
                    _register_last(tuple(traversed), tgt)
                    _register_connector_entry(parent_path, part, tgt, metadata, value)
                else:
                    plf(part, "final_value_single_connector", cl); tgt = nxt
                if value in unique_id["Item"].values:
                    plf(value, "final_value_multi_unique_id", tgt); uid = get_information_value(
                        df=unique_id,
                        row_to_look=value,
                        col_to_look="ID",
                        col_to_match="Item",
                    )
                    if not pd.isna(uid):
                        plf(uid, "final_value_multi_set_id", tgt); tgt["@id"] = uid
                    _merge_type(tgt, value)
                elif value:
                    plf(value, "final_value_multi_comment", tgt); tgt["rdfs:comment"] = value
                if part in MULTI_CONNECTORS:
                    plf(part, "final_value_multi_update_tokens", tgt); _update_entry_tokens(
                        parent_path,
                        tgt,
                        metadata,
                        value if isinstance(value, str) else None,
                    )
                break

            plf(part, "iterate_next", nxt); cl = nxt

    except Exception as e:  
        traceback.print_exc()
        raise RuntimeError(
            f"Error occurred with value '{value}' and path '{path}': {str(e)}"
        )


def plf(value: Any, part: str, current_level: Optional[dict] = None, debug_switch: bool = DEBUG_STATUS):
    """
    Print Line Function (PLF).

    This function is used for debugging purposes. It prints the current line number, 
    along with the provided value, part, and optionally the current level, if debugging 
    is enabled via the `debug_switch` parameter.

    Args:
        value (Any): The value being processed or debugged.
        part (Any): The part of the JSON-LD or data structure being processed.
        current_level (Optional[dict]): The current level of the JSON-LD or data structure, if applicable.
        debug_switch (bool): A flag to enable or disable debug output. Defaults to True.

    Returns:
        None: This function does not return any value.
    """
    if debug_switch:
        current_frame = inspect.currentframe()
        line_number = current_frame.f_back.f_lineno
        if current_level is not None:
            print(f'pass line {line_number}, value:', value,'AND part:', part, 'AND current_level:', current_level)
        else:
            print(f'pass line {line_number}, value:', value,'AND part:', part)
    else:
        pass 
