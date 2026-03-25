"""Functions to perform Excel -> JSON conversion."""

import datetime
from importlib.metadata import version
from pathlib import Path
from typing import IO

import numpy as np
import pandas as pd
from pandas import DataFrame

from . import auxiliary as aux
from .excel_tools import ExcelContainer
from .json_template import (
    rated_cap_vs_graphite,
    rated_cap_vs_li,
)
from .validate import validate_jsonld

APP_VERSION = version("battinfoconverter-backend")


def get_information_value(
    df: DataFrame, row_to_look: str, col_to_look: str = "Value", col_to_match: str = "Metadata"
) -> str | None:
    """Retrieve the value from a specified column where a different column matches a given value.

    Args:
        df (DataFrame): The DataFrame to search within.
        row_to_look (str): The value to match within the column specified by col_to_match.
        col_to_look (str): The name of the column from which to get the value. Default is "Key".
        col_to_match (str): The name of the column to search for row_to_look. Default is "Item".

    Returns:
        str | None: The value from the column col_to_look if a match is found; otherwise, None.

    """
    if row_to_look.endswith(" "):  # Check if the string ends with a space
        row_to_look = row_to_look.rstrip(" ")  # Remove only trailing spaces
    result = df.query(f"{col_to_match} == @row_to_look")[col_to_look]
    return result.iloc[0] if not result.empty else None


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

    # Harvest the information for the required section of the schemas
    ls_info_to_harvest = [
        "Cell type",
        "Cell ID",
        "Date of cell assembly",
        "Institution/company",
        "Scientist/technician/operator",
    ]

    dict_harvested_info = {}

    # Harvest the required value from the schema sheet.
    for field in ls_info_to_harvest:
        if get_information_value(df=schema, row_to_look=field) is np.nan:
            msg = f"Missing information in the schema, please fill in the field '{field}'"
            raise ValueError(msg)
        dict_harvested_info[field] = get_information_value(df=schema, row_to_look=field)

    # Harvest unique ID value for the required value from the schema sheet.
    ls_id_info_to_harvest = ["Institution/company", "Scientist/technician/operator"]
    dict_harvest_id = {}
    for uid in ls_id_info_to_harvest:
        dict_harvest_id[uid] = get_information_value(
            df=data_container.data["unique_id"],
            row_to_look=dict_harvested_info[uid],
            col_to_look="ID",
            col_to_match="Item",
        )
        if dict_harvest_id[uid] is None:
            msg = f"Missing unique ID for the field '{uid}'"
            raise ValueError(msg)

    schema_version = None
    try:
        schema_version = get_information_value(df=schema, row_to_look="Schema version")
    except Exception:
        schema_version = None
    if schema_version is None or pd.isna(schema_version):
        schema_version = get_information_value(df=schema, row_to_look="BattINFO CoinCellSchema version")
    if schema_version is None or pd.isna(schema_version):
        msg = "Missing schema version in the schema sheet"
        raise ValueError(msg)

    jsonld = {
        "@context": ["https://w3id.org/emmo/domain/battery/context", {}],
        "@type": dict_harvested_info["Cell type"],
        "schema:version": schema_version,
        "schema:productID": dict_harvested_info["Cell ID"],
        "schema:dateCreated": dict_harvested_info["Date of cell assembly"],
        "schema:creator": {
            "@type": "schema:Person",
            "@id": dict_harvest_id["Scientist/technician/operator"],
            "schema:name": dict_harvested_info["Scientist/technician/operator"],
        },
        "schema:manufacturer": {
            "@type": "schema:Organization",
            "@id": dict_harvest_id["Institution/company"],
            "schema:name": dict_harvested_info["Institution/company"],
        },
        "rdfs:comment": [],
    }

    for _, row in context_toplevel.iterrows():
        jsonld["@context"][1][row["Item"]] = row["Key"]

    jsonld["rdfs:comment"].append(f"BattINFO Converter version: {APP_VERSION}")
    jsonld["rdfs:comment"].append(
        f"Software credit: This JSON-LD was created using BattINFO converter "
        f"(https://battinfoconverter.streamlit.app/) version: {APP_VERSION} "
        f"and the schema version: {jsonld['schema:version']}, "
        "this web application was developed at Empa, Swiss Federal Laboratories for Materials "
        "Science and Technology in the Laboratory Materials for Energy Conversion"
    )

    data_container._last_nodes = {}
    data_container._path_counts = {}
    data_container._connector_registry = {}

    for _, row in schema.iterrows():
        if pd.isna(row["Value"]) or row["Ontology link"] == "NotOntologize":
            continue
        if row["Ontology link"] == "Comment":
            if row["Unit"] == "No Unit":
                jsonld["rdfs:comment"].append(f"{row['Metadata']}: {row['Value']}")
            else:
                jsonld["rdfs:comment"].append(f"{row['Metadata']}: {row['Value']} {row['Unit']}")
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
            data_container,
            metadata=row["Metadata"],
        )
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
    excel_file: str | Path | IO[bytes],
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
    if debug_mode:
        print("*********************************************************")
        print(f"Initialize new session of Excel file conversion, started at {datetime.datetime.now()}")
        print("*********************************************************")
    data_container = ExcelContainer(excel_file)

    # Generate JSON-LD using the data container
    jsonld_output = create_jsonld_with_conditions(data_container)
    jsonld_output = reformat_json_rated_capacity(jsonld_output)
    if validate:
        validate_jsonld(jsonld_output, errors="warn")
    return jsonld_output
