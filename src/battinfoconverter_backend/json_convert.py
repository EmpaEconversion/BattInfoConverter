"""Functions to perform Excel -> JSON conversion."""

import logging
from importlib.metadata import version
from pathlib import Path
from typing import IO

import pandas as pd
from openpyxl import Workbook

from . import auxiliary as aux
from .excel_tools import ExcelContainer
from .json_template import (
    rated_cap_vs_graphite,
    rated_cap_vs_li,
)
from .registry import Registry
from .validate import validate_jsonld

logger = logging.getLogger(__name__)

APP_VERSION = version("battinfoconverter-backend")


def create_jsonld_with_conditions(data_container: ExcelContainer) -> dict:
    """Create JSON-LD structure based on the provided data container containing schema and context.

    This function extracts necessary information from the schema and context sheets of the provided
    `ExcelContainer` to generate a JSON-LD object. It performs validation, handles ontology links,
    and structures data in compliance with the EMMO domain for battery context.

    Args:
        data_container (ExcelContainer): ExcelContainer of the Excel file to be converted.

    Returns:
        dict: A JSON-LD dictionary representing the structured information.

    Raises:
        ValueError: If required fields are missing or contain invalid data.

    """
    schema = data_container.data["schema"]
    context_toplevel = data_container.data["context_toplevel"]
    id_from_val: dict[str, str] = data_container.data["unique_id_map"]

    filtered = schema.loc[schema["Metadata"].isin({"Schema version", "BattINFO CoinCellSchema version"}), "Value"]
    schema_version = filtered.iloc[0] if not filtered.empty else None
    if filtered.empty:
        logger.warning("Missing schema version in the schema sheet")

    filtered = schema.loc[schema["Metadata"] == "Schema name", "Value"]
    if not filtered.empty:
        schema_name = filtered.iloc[0]
    elif "BattINFO CoinCellSchema version" in schema["Metadata"].to_numpy():
        schema_name = "CoinCellSchema"
    else:
        schema_name = None
        logger.warning("Missing schema version in the schema sheet")

    jsonld: dict[str, str | list | dict | float] = {
        "@context": [
            "https://w3id.org/emmo/domain/battery/context",
            {row["Item"]: row["Key"] for _, row in context_toplevel.iterrows()},
        ],
    }

    # Special hardcoded NotOntologize fields - required for backwards compatibility
    not_ontologize_mask = schema["Ontology link"] == "NotOntologize"

    def get_val(key):
        mask = schema[not_ontologize_mask]["Metadata"] == key
        filtered = schema[not_ontologize_mask][mask]
        if len(filtered) == 1:
            return filtered.iloc[0]["Value"]
        return None

    if val := get_val("Cell type"):
        jsonld["@type"] = val
    if val := get_val("Cell ID"):
        jsonld["schema:productID"] = val
    if val := get_val("Date of cell assembly"):
        jsonld["schema:dateCreated"] = aux.coerce_date_to_iso(val)
    if val := get_val("Scientist/technician/operator"):
        jsonld["schema:creator"] = {
            "@type": "schema:Person",
            "@id": id_from_val[val],
            "schema:name": val,
        }
    if val := get_val("Institution/company"):
        jsonld["schema:manufacturer"] = {
            "@type": "schema:Organization",
            "@id": id_from_val[val],
            "schema:name": val,
        }
    if val := get_val("Schema version"):
        jsonld["schema:version"] = val

    # Add everything else in the sheet
    registry = Registry(data_container)
    for _, row in schema.iterrows():
        if pd.isna(row["Value"]) or row["Ontology link"] == "NotOntologize":
            continue

        ontology_path = row["Ontology link"].split("-")

        # Default behavior for other entries
        if pd.isna(row["Unit"]):
            msg = f"The value '{row['Value']}' is filled in the wrong row, please check the schema"
            raise ValueError(msg)

        aux.add_to_structure(
            jsonld,
            ontology_path,
            row["Value"],
            row["Unit"],
            registry,
            metadata=row["Metadata"],
        )

    # Add or prepend root level comment
    software_credit = (
        f"Software credit: This JSON-LD was created using BattINFO converter v{APP_VERSION} "
        "(https://battinfoconverter.streamlit.app/)"
    )
    if schema_name and schema_version:
        software_credit += f" with schema: {schema_name} v{schema_version}"
    elif schema_name:
        software_credit += f" with schema: {schema_name}, unspecified version"
    elif schema_version:
        software_credit += f" with unspecified schema v{schema_version}"
    software_credit += (
        ". "
        "BattINFO converter was developed at Empa, Swiss Federal Laboratories for Materials "
        "Science and Technology in the Laboratory Materials for Energy Conversion."
    )
    root_comment = [
        f"BattINFO Converter version: {APP_VERSION}",
        software_credit,
    ]
    current_comment = jsonld.get("rdfs:comment", [])
    if not isinstance(current_comment, list):
        current_comment = [current_comment]
    jsonld["rdfs:comment"] = [*root_comment, *current_comment]

    return jsonld


def reformat_json_rated_capacity(json_dict: dict) -> dict:
    """Reformat rated capacity following template in json_template.py.

    Will only modify the dict if all required fields are present, otherwise returns the same dict.

    This function is subject to change. E.g. it is not clear how to proceed when the user input
    different reference electrodes.

    Args:
        json_dict (dict): The JSON dictionary to format.

    Returns:
        dict: The modified JSON dictionary with the rated capacity section reformatted.

    """
    original_dict = json_dict.copy()
    try:
        # Positive electrode
        sub_dict = json_dict["hasPositiveElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"]["hasInput"]
        json_dict["hasPositiveElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"] = rated_cap_vs_graphite(
            sub_dict["ConstantCurrentCharging"]["hasInput"][1]["hasNumericalPart"]["hasNumberValue"],
            sub_dict["ConstantCurrentCharging"]["hasInput"][2]["hasNumericalPart"]["hasNumberValue"],
            sub_dict["ConstantVoltageCharging"]["hasInput"][0]["hasNumericalPart"]["hasNumberValue"],
            sub_dict["ConstantVoltageCharging"]["hasInput"][1]["hasNumericalPart"]["hasNumberValue"],
            sub_dict["ConstantCurrentDischarging"]["hasInput"][1]["hasNumericalPart"]["hasNumberValue"],
            sub_dict["ConstantCurrentDischarging"]["hasInput"][2]["hasNumericalPart"]["hasNumberValue"],
        )
        # Negative electrode
        sub_dict = json_dict["hasNegativeElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"]["hasInput"]
        json_dict["hasNegativeElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"] = rated_cap_vs_li(
            sub_dict["ConstantCurrentDischarging"]["hasInput"][1]["hasNumericalPart"]["hasNumberValue"],
            sub_dict["ConstantCurrentDischarging"]["hasInput"][0]["hasNumericalPart"]["hasNumberValue"],
            sub_dict["ConstantVoltageCharging"]["hasInput"][0]["hasNumericalPart"]["hasNumberValue"],
            sub_dict["ConstantVoltageCharging"]["hasInput"][1]["hasNumericalPart"]["hasNumberValue"],
            sub_dict["ConstantCurrentCharging"]["hasInput"][1]["hasNumericalPart"]["hasNumberValue"],
            sub_dict["ConstantCurrentCharging"]["hasInput"][2]["hasNumericalPart"]["hasNumberValue"],
        )
    except (KeyError, IndexError):
        # If not enough inputs provided to reformat, use original formatting
        return original_dict
    else:
        return json_dict


def convert_excel_to_jsonld(
    excel_file: str | Path | IO[bytes] | Workbook,
    *,
    validate: bool = True,
    debug_mode: bool = False,
) -> dict:
    """Convert an Excel file into a JSON-LD representation.

    This function initializes a new session for converting an Excel file, processes the data using
    the `ExcelContainer` class, and generates a complete JSON-LD object. It uses the
    `create_jsonld_with_conditions` function to construct a structured section of the JSON-LD and
    incorporates it into the final output.

    Args:
        excel_file (ExcelContainer): ExcelContainer of the Excel file to be converted.
        validate (bool): Whether to warn about possible issues in the output. Default is True.
        debug_mode (bool): Flag to enable or disable debug mode. Default is False.

    Returns:
        dict: A JSON-LD dictionary representing the entire structured information.

    Raises:
        ValueError: If any required fields in the Excel file are missing or contain invalid data.

    """
    pkg_logger = logging.getLogger("battinfoconverter_backend")
    handler = None

    if debug_mode:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(fmt="[%(levelname)s] %(message)s")
        handler.setFormatter(formatter)
        pkg_logger.setLevel(logging.DEBUG)
        pkg_logger.addHandler(handler)
        pkg_logger.propagate = False
        logger.debug("Started Excel file conversion with debug messages")

    try:
        data_container = ExcelContainer(excel_file)
        jsonld_output = create_jsonld_with_conditions(data_container)
        jsonld_output = reformat_json_rated_capacity(jsonld_output)
        if validate:
            validate_jsonld(jsonld_output, errors="warn")
        return jsonld_output
    finally:
        if handler is not None:
            pkg_logger.removeHandler(handler)
            pkg_logger.setLevel(logging.INFO)
            pkg_logger.propagate = True
