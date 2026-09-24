"""Functions to perform Excel -> JSON conversion."""

import logging
import re
from importlib.metadata import version
from pathlib import Path
from typing import IO, Any

import pandas as pd
from openpyxl import Workbook

from . import auxiliary as aux
from .excel_tools import ExcelContainer
from .json_template import (
    half_cell_chg_cap,
    half_cell_dchg_cap,
)
from .registry import Registry
from .validate import validate_jsonld

logger = logging.getLogger(__name__)

APP_VERSION = version("battinfoconverter-backend")

# Cell types tested by an ElectrolysisTest rather than a BatteryTest
ELECTROLYSIS_CELL_TYPES = {
    "ElectrolyticCell",
    "PhotoelectrolyticCell",
    "Electrolyser",
}

# The @References row that switches the whole sheet on, matched by its start so
# the wording can carry a hint such as "(yes/no)"
INCLUDE_FIELD = "Include references"

ORGANIZATION_TYPE = "schema:ResearchOrganization"

# The dataset type added alongside the test result type
DATASET_TYPE = "dcat:Dataset"

FIGURE_COMMENT = "Subfigure of associated peer-reviewed scientific publication containing this data"

# Labels of the @References rows describing the publication this data belongs to
PUBLICATION_PREFIX = "Associated publication"

# @References labels mapped to their predicate and how their cells are read,
# in the order they appear in the output. Rows labelled with a trailing letter
# (e.g. "Dataset authorA") are collected into one list, as elsewhere in the schema.
EXTRA_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("Dataset name", "dcterms:title", "text"),
    ("Dataset description", "dcterms:description", "text"),
    ("Dataset author", "dcterms:creator", "people"),
    ("Dataset publisher", "dcterms:publisher", "organization"),
    ("Dataset license", "dcterms:license", "text"),
    ("Dataset date issued", "dcterms:issued", "date"),
    ("Dataset date published", "schema:datePublished", "date"),
    ("Dataset keywords", "dcat:keyword", "list"),
    ("Dataset URL", "dcat:accessURL", "text"),
    ("Dataset API URL", "dcat:endpointURL", "text"),
    (PUBLICATION_PREFIX, "schema:associatedMedia", "publication"),
)

# A row label ending in a single capital, e.g. "Dataset authorA"
_SUFFIXED_LABEL = re.compile(r"^(?P<base>.*[a-z])(?P<suffix>[A-Z])$")


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

    local_context: dict[str, str | dict] = {row["Item"]: row["Key"] for _, row in context_toplevel.iterrows()}
    # @vocab routes bare unit labels through the context's term definitions,
    # so "Volt" expands to the real EMMO IRI instead of a document-relative one
    local_context.setdefault(
        "hasMeasurementUnit",
        {
            "@id": "https://w3id.org/emmo#EMMO_bed1d005_b04e_4a90_94cf_02bc678a8569",
            "@type": "@vocab",
        },
    )
    jsonld: dict[str, str | list | dict | float] = {
        "@context": [
            "https://w3id.org/emmo/domain/battery/context",
            local_context,
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

    return jsonld


def add_credit_comments(jsonld: dict, schema: pd.DataFrame, software_credit: str | None = None) -> None:
    """Prepend the converter, template and software credit comments to the root node."""
    if software_credit:
        software_credit = f"Software credit: {software_credit}"
    else:
        software_credit = (
            "Software credit: This JSON-LD was created using the BattINFO Converter Python package "
            "(https://github.com/EmpaEconversion/BattInfoConverter), "
            "developed at Empa, Swiss Federal Laboratories for Materials Science and Technology "
            "in the Laboratory Materials for Energy Conversion."
        )

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

    if schema_name and schema_version:
        schema_str = f"{schema_name} v{schema_version}"
    elif schema_name:
        schema_str = f"{schema_name}, unspecified version"
    elif schema_version:
        schema_str = f"unspecified schema v{schema_version}"
    else:
        schema_str = "unspecified"

    root_comment = [
        f"BattINFO Converter backend v{APP_VERSION}",
        f"Using template: {schema_str}",
        software_credit,
    ]
    current_comment = jsonld.get("rdfs:comment", [])
    if not isinstance(current_comment, list):
        current_comment = [current_comment]
    jsonld["rdfs:comment"] = [*root_comment, *current_comment]


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
        json_dict["hasPositiveElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"] = half_cell_chg_cap(
            sub_dict["ElectrochemicalHalfCell"]["hasReferenceElectrode"]["@type"][-1],
            sub_dict["ConstantCurrentCharging"]["hasInput"][1]["hasNumericalPart"]["hasNumberValue"],
            sub_dict["ConstantCurrentCharging"]["hasInput"][2]["hasNumericalPart"]["hasNumberValue"],
            sub_dict["ConstantVoltageCharging"]["hasInput"][0]["hasNumericalPart"]["hasNumberValue"],
            sub_dict["ConstantVoltageCharging"]["hasInput"][1]["hasNumericalPart"]["hasNumberValue"],
            sub_dict["ConstantCurrentDischarging"]["hasInput"][1]["hasNumericalPart"]["hasNumberValue"],
            sub_dict["ConstantCurrentDischarging"]["hasInput"][2]["hasNumericalPart"]["hasNumberValue"],
        )
        # Negative electrode
        sub_dict = json_dict["hasNegativeElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"]["hasInput"]
        json_dict["hasNegativeElectrode"]["hasMeasuredProperty"][0]["@reverse"]["hasOutput"] = half_cell_dchg_cap(
            sub_dict["ElectrochemicalHalfCell"]["hasReferenceElectrode"]["@type"][-1],
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


def _is_yes(value: object) -> bool:
    """Interpret an Excel yes/no cell."""
    if isinstance(value, str):
        return value.strip().lower() in {"yes", "y", "true", "1"}
    return value is True or value == 1


def _named_node(node_type: str, name: str, id_from_val: dict[str, str]) -> dict:
    """Create a named node, with an @id if one is listed in @Classes."""
    node = {"@type": node_type}
    if name in id_from_val:
        node["@id"] = id_from_val[name]
    node["schema:name"] = name
    return node


def _parse_extra_rows(rows: list[list]) -> tuple[dict, dict]:
    """Split the @References rows into single fields and groups of suffixed rows.

    A row labelled with a trailing letter, e.g. "Dataset authorA", joins the group
    "Dataset author"; each of its entries is a name followed by any affiliations.
    """
    fields: dict[str, list] = {}
    groups: dict[str, list[tuple[str, dict]]] = {}
    for key, *values in rows:
        if not values:
            continue
        label = str(key)
        match = _SUFFIXED_LABEL.match(label)
        if match:
            name, *affiliations = values
            entry = {"name": str(name), "affiliations": [str(v) for v in affiliations]}
            groups.setdefault(match["base"], []).append((match["suffix"], entry))
        else:
            fields[label] = values
    return fields, {base: [e for _, e in sorted(entries)] for base, entries in groups.items()}


def _author_node(author: dict, id_from_val: dict[str, str]) -> dict:
    """Create a person node with its affiliations."""
    person = _named_node("schema:Person", author["name"], id_from_val)
    affiliations = [_named_node(ORGANIZATION_TYPE, aff, id_from_val) for aff in author["affiliations"]]
    if affiliations:
        person["schema:affiliation"] = affiliations[0] if len(affiliations) == 1 else affiliations
    return person


def _publication_node(fields: dict[str, list], groups: dict, id_from_val: dict[str, str]) -> dict | None:
    """Create the node describing the publication this data belongs to."""

    def first(suffix: str) -> str | None:
        values = fields.get(f"{PUBLICATION_PREFIX} {suffix}", [])
        return values[0] if values else None

    doi, title = first("DOI"), first("title")
    figures = fields.get(f"{PUBLICATION_PREFIX} figures", [])
    authors = groups.get(f"{PUBLICATION_PREFIX} author", [])
    if not any((doi, title, figures, authors)):
        return None

    node: dict[str, Any] = {}
    if doi:
        node["@id"] = doi
    if title:
        node["dcterms:title"] = title
    if authors:
        node["dcterms:creator"] = [_author_node(author, id_from_val) for author in authors]
    if figures:
        node["rdfs:label"] = [str(label) for label in figures]
        node["rdfs:comment"] = FIGURE_COMMENT
    return node


def _dataset_node(fields: dict[str, list], groups: dict, id_from_val: dict[str, str], result_type: str) -> dict:
    """Create the test result node from the @References rows."""
    output: dict[str, Any] = {"@type": [result_type, DATASET_TYPE]}
    for label, predicate, kind in EXTRA_FIELDS:
        if kind == "publication":
            if node := _publication_node(fields, groups, id_from_val):
                output[predicate] = node
            continue
        values = groups.get(label, []) if kind == "people" else fields.get(label, [])
        if not values:
            continue
        if kind == "text":
            output[predicate] = values[0]
        elif kind == "date":
            output[predicate] = aux.coerce_date_to_iso(values[0])
        elif kind == "list":
            output[predicate] = list(values)
        elif kind == "people":
            output[predicate] = [_author_node(author, id_from_val) for author in values]
        elif kind == "organization":
            output[predicate] = _named_node(ORGANIZATION_TYPE, values[0], id_from_val)
    return output


def wrap_in_test(jsonld: dict, data_container: ExcelContainer) -> dict:
    """Move the cell under a test node with publication information, if requested in @Extra.

    The test becomes the root node, the cell becomes its hasTestObject, and the
    publication information is attached as its hasOutput. The test type follows
    from the cell type. The cell keeps its own comments.
    """
    rows = data_container.data.get("extra_rows")
    if not rows:
        return jsonld
    fields, groups = _parse_extra_rows(rows)
    include = next((v for label, v in fields.items() if label.startswith(INCLUDE_FIELD)), [None])
    if not _is_yes(include[0]):
        return jsonld
    id_from_val: dict[str, str] = data_container.data["unique_id_map"]

    cell_type = jsonld.get("@type", [])
    cell_types = {cell_type} if isinstance(cell_type, str) else set(cell_type)
    test_type = "ElectrolysisTest" if cell_types & ELECTROLYSIS_CELL_TYPES else "BatteryTest"

    context = jsonld.pop("@context")
    return {
        "@context": context,
        "@type": test_type,
        "hasTestObject": jsonld,
        "hasOutput": _dataset_node(fields, groups, id_from_val, f"{test_type}Result"),
    }


def convert_excel_to_jsonld(
    excel_file: str | Path | IO[bytes] | Workbook,
    *,
    software_credit: str | None = None,
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
        software_credit (str): String to add into comments for 'Software credit'.
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
        jsonld_output = wrap_in_test(jsonld_output, data_container)
        add_credit_comments(jsonld_output, data_container.data["schema"], software_credit)
        if validate:
            validate_jsonld(jsonld_output, errors="warn")
        return jsonld_output
    finally:
        if handler is not None:
            pkg_logger.removeHandler(handler)
            pkg_logger.setLevel(logging.INFO)
            pkg_logger.propagate = True
