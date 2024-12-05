import pandas as pd
import traceback
import inspect

def add_to_structure(jsonld, path, value, unit, data_container):
    from json_convert import get_information_value
    try:
        print('               ')  # To add space between each Excel row - for debugging.
        current_level = jsonld
        unit_map = data_container.data['unit_map'].set_index('Item').to_dict(orient='index')
        context_connector = data_container.data['context_connector']
        connectors = set(context_connector['Item'])
        unique_id = data_container.data['unique_id']

        for idx, parts in enumerate(path):
            if len(parts.split('|')) == 1:
                part = parts
                special_command = None
                plf(value, part)

            elif "type|" in parts:
                # Handle "type|" special command
                _, type_value = parts.split('|', 1)
                plf(value, type_value)

                # Assign type value
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
                plf(value, part)
                if part in connectors:
                    plf(value, part)
                    connector_type = context_connector.loc[context_connector['Item'] == part, 'Key'].values[0]
                    if pd.isna(connector_type):
                        plf(value, part)
                        current_level[part] = {}
                    else:
                        plf(value, part)
                        current_level[part] = {"@type": connector_type}
                else:
                    plf(value, part)
                    current_level[part] = {}

            # Handle the case of the single path
            if len(path) == 1 and unit == 'No Unit':
                plf(value, part)
                if value in unique_id['Item'].values:
                    plf(value, part)
                    if "@type" in current_level:
                        plf(value, part)
                        if "@type" in current_level[part] and isinstance(current_level[part]["@type"], list):
                            plf(value, part)
                            if not pd.isna(value):
                                plf(value, part)
                                current_level[part]["@type"].append(value)
                        else:
                            plf(value, part)
                            if not pd.isna(value):
                                plf(value, part)
                                current_level[part]["@type"] = [value]
                    else:
                        plf(value, part)
                        if not pd.isna(value):
                            plf(value, part)
                            current_level[part]["@type"] = value
                else:
                    plf(value, part)
                    current_level[part]['rdfs:comment'] = value
                break

            if is_last and unit == 'No Unit':
                plf(value, part)
                if value in unique_id['Item'].values:
                    plf(value, part)
                    if "@type" in current_level:
                        plf(value, part)
                        if isinstance(current_level["@type"], list):
                            plf(value, part)
                            if not pd.isna(value):
                                current_level["@type"].append(value)
                        else:
                            plf(value, part)
                            if not pd.isna(value):
                                current_level["@type"] = [current_level["@type"], value]
                    else:
                        if not pd.isna(value):
                            current_level["@type"] = value
                else:
                    current_level['rdfs:comment'] = value
                break

            current_level = current_level[part]

    except Exception as e:
        traceback.print_exc()  # Print the full traceback
        raise RuntimeError(f"Error occurred with value '{value}' and path '{path}': {str(e)}")


def plf(value, part, current_level = None, debug_switch = True):
    """Print Line Function.
    This function is used for debugging.
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
