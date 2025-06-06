import pandas as pd
import traceback
import inspect
from typing import Any, Optional

DEBUG_STATUS = False # Set to True for debugging output (using plf function)

def add_to_structure(
    jsonld: dict,
    path: list[str],
    value: Any,
    unit: str,
    data_container: "ExcelContainer",
) -> None:
    """
    Build or extend *jsonld* along *path* with *value* and *unit*.

    Key features
    ------------
    • Handles special commands ``type|`` and ``rev|`` exactly as before.  
    • Prevents silent overwrites of ``@type`` or measured-property blocks.  
    • Connector rows that can appear **multiple times** (e.g. solvents,
      additives) are stored as *lists of separate objects*; everything else
      remains a single dict, so existing client code (e.g. manufacturer) keeps
      working.

    The set of multi-object connectors can be expanded easily by editing
    ``MULTI_CONNECTORS`` below.
    """
    # ------------------------------------------------------------------ #
    # Which connector keys should become lists (one object per row)      #
    # ------------------------------------------------------------------ #
    MULTI_CONNECTORS = {
        "hasConstituent",
        "hasAdditive",
        "hasSolute",
        "hasSolvent",
    }

    # ------------------------------------------------------------------ #
    # Local helpers                                                      #
    # ------------------------------------------------------------------ #
    def _merge_type(node: dict, new_type: str) -> None:
        if "@type" not in node:
            node["@type"] = new_type
        else:
            ex = node["@type"]
            if isinstance(ex, list):
                if new_type not in ex:
                    ex.append(new_type)
            elif ex != new_type:
                node["@type"] = [ex, new_type]

    def _add_or_extend_list(node: dict, key: str, new_entry: dict) -> None:
        cur = node.get(key)
        if cur in (None, {}):
            node[key] = new_entry
        elif isinstance(cur, list):
            cur.append(new_entry)
        else:
            node[key] = [cur, new_entry]

    def _extract_type(seg: str) -> str:
        return seg.split("|", 1)[1] if seg.startswith("type|") else seg

    def _make_fresh_item(parent: dict, key: str) -> dict:
        """Convert *parent[key]* into a list and append a fresh dict."""
        val = parent.get(key)
        if val is None or val == {}:
            parent[key] = {}
            return parent[key]
        if isinstance(val, list):
            new_obj = {}
            val.append(new_obj)
            return new_obj
        parent[key] = [val, {}]
        return parent[key][-1]

    # ------------------------------------------------------------------ #
    # Main body                                                          #
    # ------------------------------------------------------------------ #
    from json_convert import get_information_value
    try:
        current_level = jsonld
        unit_map = (
            data_container.data["unit_map"].set_index("Item").to_dict(orient="index")
        )
        context_connector = data_container.data["context_connector"]
        connectors = set(context_connector["Item"])
        unique_id = data_container.data["unique_id"]

        if not value or pd.isna(value):
            return

        for idx, parts in enumerate(path):
            # ----------- handle special-command segments --------------- #
            if "|" not in parts:
                part = parts
            elif "type|" in parts:
                _, tval = parts.split("|", 1)
                if tval:
                    _merge_type(current_level, tval)
                continue
            else:
                cmd, part = parts.split("|")
                if cmd == "rev":
                    current_level = current_level.setdefault("@reverse", {})
                else:
                    raise ValueError(f"Unknown special command {cmd} in {parts}")

            # If we’re already inside a list (from previous row), point to last
            if isinstance(current_level, list):
                current_level = current_level[-1]

            is_last = idx == len(path) - 1
            is_second_last = idx == len(path) - 2

            # ----------- create node if absent ------------------------- #
            if part not in current_level and (value or unit):
                if part in connectors:
                    ctype = context_connector.loc[
                        context_connector["Item"] == part, "Key"
                    ].values[0]
                    current_level[part] = {} if pd.isna(ctype) else {"@type": ctype}
                else:
                    current_level[part] = {}

            next_level = current_level[part]

            # ----------- measured-property branch ---------------------- #
            if is_second_last and unit != "No Unit":
                if pd.isna(unit):
                    raise ValueError(f"Value '{value}' missing unit.")

                unit_info = unit_map.get(unit, {})
                new_entry = {
                    "@type": _extract_type(path[-1]),
                    "hasNumericalPart": {
                        "@type": "emmo:RealData",     # updated label
                        "hasNumberValue": value,      # updated key
                    },
                    "hasMeasurementUnit": unit_info.get("Key", "UnknownUnit"),
                }

                # --- FIX: choose the right parent ------------------------
                target_parent = current_level[-1] if isinstance(current_level, list) else current_level
                _add_or_extend_list(target_parent, part, new_entry)
                # ---------------------------------------------------------
                break

            # ----------- final-value branch ----------------------------- #
            if is_last and unit == "No Unit":
                # Only MULTI_CONNECTORS are turned into lists
                if part in MULTI_CONNECTORS:
                    target = _make_fresh_item(current_level, part)
                else:
                    target = next_level

                if value in unique_id["Item"].values:
                    uid = get_information_value(
                        df=unique_id,
                        row_to_look=value,
                        col_to_look="ID",
                        col_to_match="Item",
                    )
                    if not pd.isna(uid):
                        target["@id"] = uid
                    _merge_type(target, value)
                elif value:
                    target["rdfs:comment"] = value
                break

            current_level = next_level

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
