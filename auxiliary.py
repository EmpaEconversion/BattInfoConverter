import inspect
import pandas as pd
import traceback
from decimal import Decimal
from typing import Any, Optional

DEBUG_STATUS = False 

def add_to_structure(
    jsonld: dict,
    path: list[str],
    value: Any,
    unit: str,
    data_container: "json_convert.ExcelContainer",
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
            node["@type"] = new_type
        else:
            ex = node["@type"]
            if isinstance(ex, list):
                if new_type not in ex:
                    ex.append(new_type)
            elif ex != new_type:
                node["@type"] = [ex, new_type]

    def _add_or_extend_list(node: dict, key: str, entry: dict) -> None:
        cur = node.get(key)
        if cur in (None, {}):
            node[key] = entry
        elif isinstance(cur, list):
            cur.append(entry)
        else:
            node[key] = [cur, entry]

    def _extract_type(seg: str) -> str:
        return seg.split("|", 1)[1] if seg.startswith("type|") else seg

    def _new_item(parent: dict, key: str) -> dict:
        val = parent.get(key)
        if val in (None, {}):
            parent[key] = {}
            return parent[key]
        if isinstance(val, list):
            fresh = {}
            val.append(fresh)
            return fresh
        parent[key] = [val, {}]
        return parent[key][-1]

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
            return
        # ---------------------------------------------------------------- #

        for idx, parts in enumerate(path):
            # ---------- special-command parsing ------------------------- #
            if "|" not in parts:
                part = parts
            elif "type|" in parts:
                _, typ = parts.split("|", 1)
                if typ:
                    _merge_type(cl, typ)
                continue
            else:  # rev|
                cmd, part = parts.split("|", 1)
                if cmd == "rev":
                    cl = cl.setdefault("@reverse", {})
                else:
                    raise ValueError(f"Unknown command {cmd} in {parts}")

            if isinstance(cl, list):
                cl = cl[-1]

            last  = idx == len(path) - 1
            penul = idx == len(path) - 2

            # -------- create node if missing ---------------------------- #
            if part not in cl and (value or unit):
                if part in connectors:
                    ctype = ctx_conn.loc[ctx_conn["Item"] == part, "Key"].values[0]
                    cl[part] = {} if pd.isna(ctype) else {"@type": ctype}
                else:
                    cl[part] = {}

            nxt = cl[part]

            # -------- measured-property block --------------------------- #
            if penul and unit != "No Unit":
                if pd.isna(unit):
                    raise ValueError(f"Value '{value}' missing unit.")
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
                _add_or_extend_list(parent, part, mp_entry)
                break

            # -------- final-value branch -------------------------------- #
            if last and unit == "No Unit":
                tgt = _new_item(cl, part) if part in MULTI_CONNECTORS else nxt
                if value in unique_id["Item"].values:
                    uid = get_information_value(
                        df=unique_id,
                        row_to_look=value,
                        col_to_look="ID",
                        col_to_match="Item",
                    )
                    if not pd.isna(uid):
                        tgt["@id"] = uid
                    _merge_type(tgt, value)
                elif value:
                    tgt["rdfs:comment"] = value
                break

            cl = nxt

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
