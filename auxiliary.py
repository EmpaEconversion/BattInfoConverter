import pandas as pd
import traceback
import inspect
from typing import Any, Optional

def add_to_structure(jsonld: dict, path: list[str], value: Any, unit: str, data_container: 'ExcelContainer') -> None:
    """
    Adds a value to a JSON-LD structure at a specified path, incorporating units and other contextual information.

    This function processes a path to traverse or modify the JSON-LD structure and handles special cases like 
    measured properties, ontology links, and unique identifiers. It uses data from the provided `ExcelContainer` 
    to resolve unit mappings and context connectors.

    Args:
        jsonld (dict): The JSON-LD structure to modify.
        path (list[str]): A list of strings representing the hierarchical path in the JSON-LD where the value should be added.
        value (any): The value to be inserted at the specified path.
        unit (str): The unit associated with the value. If 'No Unit', the value is treated as unitless.
        data_container (ExcelContainer): An instance of the `ExcelContainer` dataclass (from son_convert module) containing supporting data 
                                         for unit mappings, connectors, and unique identifiers.

    Returns:
        None: This function modifies the JSON-LD structure in place.

    Raises:
        ValueError: If the value is invalid, a required unit is missing, or an error occurs during path processing.
        RuntimeError: If any unexpected error arises while processing the value and path.
    """
    from json_convert import get_information_value
    try:
        print('               ')  # Debug separator
        current_level = jsonld
        unit_map = data_container.data['unit_map'].set_index('Item').to_dict(orient='index')
        context_connector = data_container.data['context_connector']
        connectors = set(context_connector['Item'])
        unique_id = data_container.data['unique_id']

        # Skip processing if value is invalid
        if not value or pd.isna(value):
            print(f"Skipping empty value for path: {path}")
            return

        for idx, parts in enumerate(path):
            if len(parts.split('|')) == 1:
                part = parts
                special_command = None
                plf(value, part)

            elif "type|" in parts:
                # Handle "type|" special command
                _, type_value = parts.split('|', 1)
                plf(value, type_value)

                # Assign type value only if it's valid
                if type_value:
                    current_level["@type"] = type_value
                plf(value, type_value, current_level=current_level)
                continue

            elif len(parts.split('|')) == 2:
                special_command, part = parts.split('|')
                plf(value, part)
                if special_command == "rev":
                    plf(value, part)
                    if "@reverse" not in current_level:
                        plf(value, part)
                        current_level["@reverse"] = {}
                    current_level = current_level["@reverse"]
                    plf(value, part)

            else:
                raise ValueError(f"Invalid JSON-LD at: {parts} in {path}")

            is_last = idx == len(path) - 1
            is_second_last = idx == len(path) - 2

            if part not in current_level:
                if value or unit:  # Only add the part if value or unit exists
                    plf(value, part)
                    if part in connectors:
                        connector_type = context_connector.loc[context_connector['Item'] == part, 'Key'].values[0]
                        if pd.isna(connector_type):
                            current_level[part] = {}
                        else:
                            current_level[part] = {"@type": connector_type}
                    else:
                        current_level[part] = {}

            # Handle unit-based measured properties
            if is_second_last and unit != 'No Unit':
                if pd.isna(unit):
                    raise ValueError(f"The value '{value}' is missing a valid unit.")
                unit_info = unit_map.get(unit, {})
                new_entry = {
                    "@type": path[-1],
                    "hasNumericalPart": {
                        "@type": "emmo:Real",
                        "hasNumericalValue": value
                    },
                    "hasMeasurementUnit": unit_info.get('Key', 'UnknownUnit')
                }
                if isinstance(current_level.get(part), list):
                    current_level[part].append(new_entry)
                else:
                    current_level[part] = new_entry
                break

            # Handle final value assignment
            if is_last and unit == 'No Unit':
                if value in unique_id['Item'].values:
                    unique_id_of_value = get_information_value(
                        df=unique_id, row_to_look=value, col_to_look="ID", col_to_match="Item"
                    )
                    if not pd.isna(unique_id_of_value):  # Only assign if the ID is valid
                        current_level["@id"] = unique_id_of_value
                    current_level["@type"] = value
                elif value:
                    current_level["rdfs:comment"] = value
                break

            current_level = current_level[part]

    except Exception as e:
        traceback.print_exc()  # Print the full traceback
        raise RuntimeError(f"Error occurred with value '{value}' and path '{path}': {str(e)}")


def plf(value: Any, part: str, current_level: Optional[dict] = None, debug_switch: bool = True):
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
