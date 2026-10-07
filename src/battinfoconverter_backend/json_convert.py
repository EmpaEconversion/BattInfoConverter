"""Functions to perform Excel -> JSON conversion."""

import logging
import re
from importlib.metadata import version
from pathlib import Path
from typing import IO, Any
from urllib.parse import quote

import pandas as pd
from openpyxl import Workbook

from . import auxiliary as aux
from .excel_tools import ExcelContainer
from .json_template import (
    half_cell_chg_cap,
    half_cell_dchg_cap,
)
from .registry import Registry
from .validate import map_context, validate_jsonld

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

# Labels of the @References rows listing the files of the dataset
DATA_FILE_PREFIX = "Data file"
RAW_FILE_PREFIX = "Raw data file"
ZIP_FIELD = "Data zip file"
TABLE_SCHEMA_FIELD = "Tabular data schema"

RAW_DATA_TYPE = "RawData"
DISTRIBUTION_TYPE = "dcat:Distribution"

# Media types are identified by their IANA IRI, not by their name
IANA_MEDIA_TYPES = "https://www.iana.org/assignments/media-types/"

# Media type of a data file, by extension
DEFAULT_MEDIA_TYPE = "application/octet-stream"
MEDIA_TYPES = {
    ".parquet": "application/vnd.apache.parquet",
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    ".json": "application/json",
    ".jsonld": "application/ld+json",
    ".txt": "text/plain",
    ".png": "image/png",
    ".pdf": "application/pdf",
    ".zip": "application/zip",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".mps": "text/plain",
}

# Tabular files get the schema of the dataset, CSV also gets its dialect
TABULAR_SUFFIXES = (".csv", ".tsv", ".parquet")
CSV_DIALECT = {"@type": "csvw:Dialect", "csvw:delimiter": ",", "csvw:skipRows": 0}

# @References labels mapped to their predicate and how their cells are read,
# in the order they appear in the output. Rows labelled with a trailing letter
# (e.g. "Dataset authorA") are collected into one list, as elsewhere in the schema.
EXTRA_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("Dataset name", "dcterms:title", "text"),
    ("Dataset description", "dcterms:description", "text"),
    ("Dataset author", "dcterms:creator", "people"),
    ("Dataset publisher", "dcterms:publisher", "organization"),
    ("Dataset license", "dcterms:license", "url"),
    ("Dataset date issued", "dcterms:issued", "date"),
    ("Dataset date published", "schema:datePublished", "date"),
    ("Dataset keywords", "dcat:keyword", "list"),
    ("Dataset URL", "dcat:accessURL", "url"),
    ("Dataset API URL", "dcat:endpointURL", "url"),
    (DATA_FILE_PREFIX, "dcat:distribution", "files"),
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
    individuals = Individuals(data_container.data)

    local_context: dict[str, str | dict] = {row["Term"]: row["IRI"] for _, row in context_toplevel.iterrows()}
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
        jsonld["schema:creator"] = individuals.node(val, "schema:Person")
    if val := get_val("Institution/company"):
        jsonld["schema:manufacturer"] = individuals.node(val, "schema:Organization")
    if val := get_val("Schema version"):
        jsonld["schema:version"] = val

    # Add everything else in the sheet
    registry = Registry(data_container)
    # Values are checked against the context as they are placed, so build the term
    # map now and quietly - validate_jsonld reports on the finished document
    registry.mapped_context = map_context(jsonld["@context"], errors="ignore")
    for _, row in schema.iterrows():
        if pd.isna(row["Value"]) or row["Ontology link"] == "NotOntologize":
            continue

        ontology_path = row["Ontology link"].split("-")

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


def _last_type(node: dict) -> str:
    """Get a node's most specific class, which is the last one added to its @type."""
    node_type = node["@type"]
    return node_type[-1] if isinstance(node_type, list) else node_type


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
            _last_type(sub_dict["ElectrochemicalHalfCell"]["hasReferenceElectrode"]),
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
            _last_type(sub_dict["ElectrochemicalHalfCell"]["hasReferenceElectrode"]),
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


class Individuals:
    """The named individuals of a workbook, from @Individuals and legacy @Classes."""

    def __init__(self, data: dict) -> None:
        """Take the IRI and class of each individual from the loaded sheets."""
        self.iri: dict[str, str] = data["unique_id_map"]
        self.classes: dict[str, str] = data["individual_types"]

    def node(self, name: str, role_type: str) -> dict:
        """Create a named node, typed by the sheet where it says, else by its role."""
        node = {"@type": self.classes.get(name) or role_type}
        if iri := self.iri.get(name):
            node["@id"] = iri
        node["schema:name"] = name
        return node


def _parse_extra_rows(rows: list[list]) -> tuple[dict, dict]:
    """Split the @References rows into single fields and groups of suffixed rows.

    A row labelled with a trailing letter, e.g. "Dataset authorA", joins the group
    "Dataset author"; each of its entries is a name followed by any affiliations.
    """
    fields: dict[str, list] = {}
    groups: dict[str, list[tuple[str, list]]] = {}
    for key, *values in rows:
        if not values:
            continue
        label = str(key)
        match = _SUFFIXED_LABEL.match(label)
        if match:
            groups.setdefault(match["base"], []).append((match["suffix"], [str(v) for v in values]))
        else:
            fields[label] = values
    return fields, {base: [cells for _, cells in sorted(entries)] for base, entries in groups.items()}


def _author_node(cells: list, individuals: Individuals) -> dict:
    """Create a person node from an author row: a name followed by any affiliations."""
    name, *affiliation_names = cells
    person = individuals.node(name, "schema:Person")
    affiliations = [individuals.node(aff, ORGANIZATION_TYPE) for aff in affiliation_names]
    if affiliations:
        person["schema:affiliation"] = affiliations[0] if len(affiliations) == 1 else affiliations
    return person


def _zenodo_record_id(dataset_url: str | None) -> str | None:
    """Get the record ID out of a Zenodo DOI or record URL, if that is what it is."""
    if not dataset_url:
        return None
    match = re.search(r"zenodo[./](?P<record>\d+)", str(dataset_url))
    return match["record"] if match else None


def _download_url(path: str, record_id: str | None, zip_name: str | None) -> str | None:
    """Build where a file can be downloaded, once the dataset is on Zenodo.

    This is the file's location, kept apart from its `@id`, which stays the path
    inside the dataset so it does not change when the dataset is published. Zenodo
    cannot link into a zip, so for a zipped dataset the path within it is a fragment.
    """
    if not record_id:
        return None
    base = f"https://zenodo.org/records/{record_id}/files"
    if zip_name:
        return f"{base}/{quote(zip_name, safe='')}#{quote(path)}"
    return f"{base}/{quote(path)}"


def _distribution_node(cells: list, fields: dict[str, list], schema: object, *, raw: bool) -> dict:
    """Create the node describing one file of the dataset.

    The row is a path within the dataset, optionally followed by a description. A
    published file is identified by where it can be downloaded; one that is not
    published yet has no identifier, only its path within the dataset.
    """
    path, *rest = cells
    suffix = Path(path).suffix.lower()
    url = _download_url(
        path,
        _zenodo_record_id(fields.get("Dataset URL", [None])[0]),
        fields.get(ZIP_FIELD, [None])[0],
    )

    node: dict[str, Any] = {}
    if url:
        node["@id"] = url
    node["@type"] = [DISTRIBUTION_TYPE, RAW_DATA_TYPE] if raw else DISTRIBUTION_TYPE
    if not url:
        node["dcterms:identifier"] = path
    node["dcat:mediaType"] = {"@id": f"{IANA_MEDIA_TYPES}{MEDIA_TYPES.get(suffix, DEFAULT_MEDIA_TYPE)}"}
    if schema and suffix in TABULAR_SUFFIXES:
        node["csvw:tableSchema"] = schema
        if suffix in (".csv", ".tsv"):
            node["csvw:dialect"] = dict(CSV_DIALECT)
    if rest and rest[0]:
        node["rdfs:comment"] = rest[0]
    if url:
        node["dcat:downloadURL"] = {"@id": url}
    return node


def _distributions(groups: dict, prefix: str, fields: dict[str, list], *, raw: bool = False) -> list[dict]:
    """Create the file nodes of one row family, in sheet order."""
    entries = groups.get(prefix, [])
    # Resolved once, so a schema that is not a URL is only reported once
    schema = fields.get(TABLE_SCHEMA_FIELD, [None])[0]
    if schema and any(Path(cells[0]).suffix.lower() in TABULAR_SUFFIXES for cells in entries):
        schema = _link_value(schema, TABLE_SCHEMA_FIELD)
    return [_distribution_node(cells, fields, schema, raw=raw) for cells in entries]


def _publication_node(fields: dict[str, list], groups: dict, individuals: Individuals) -> dict | None:
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
        node["dcterms:creator"] = [_author_node(author, individuals) for author in authors]
    if figures:
        node["rdfs:label"] = [str(label) for label in figures]
        node["rdfs:comment"] = FIGURE_COMMENT
    return node


def _link_value(value: object, label: str) -> object:
    """Write a link as a node, so it stays a link without help from the context.

    A term is only a link if the context says "@type": "@id", which is easily lost
    when documents with different contexts are merged; an "@id" always is one.
    A value that cannot be a link is kept as text, and the user is told.
    """
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        return {"@id": value}
    logger.warning(
        "'%s' should be a URL so it can be linked, '%s' is written as text instead",
        label,
        value,
    )
    return value


def _simple_value(kind: str, values: list, individuals: Individuals, label: str = "") -> object:
    """Turn the cells of one row into the value of its predicate."""
    if kind == "url":
        return _link_value(values[0], label)
    if kind == "date":
        return aux.coerce_date_to_iso(values[0])
    if kind == "list":
        return list(values)
    if kind == "people":
        return [_author_node(cells, individuals) for cells in values]
    if kind == "organization":
        return individuals.node(values[0], ORGANIZATION_TYPE)
    return values[0]


def _dataset_node(fields: dict[str, list], groups: dict, individuals: Individuals, result_type: str) -> dict:
    """Create the test result node from the @References rows."""
    output: dict[str, Any] = {"@type": [result_type, DATASET_TYPE]}
    for label, predicate, kind in EXTRA_FIELDS:
        if kind == "publication":
            if node := _publication_node(fields, groups, individuals):
                output[predicate] = node
        elif kind == "files":
            if distributions := _distributions(groups, label, fields):
                output[predicate] = distributions
        elif values := (groups.get(label, []) if kind == "people" else fields.get(label, [])):
            output[predicate] = _simple_value(kind, values, individuals, label)
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
    individuals = Individuals(data_container.data)

    cell_type = jsonld.get("@type", [])
    cell_types = {cell_type} if isinstance(cell_type, str) else set(cell_type)
    test_type = "ElectrolysisTest" if cell_types & ELECTROLYSIS_CELL_TYPES else "BatteryTest"

    context = jsonld.pop("@context")
    wrapped: dict[str, Any] = {
        "@context": context,
        "@type": test_type,
        "hasTestObject": jsonld,
    }
    if raw_files := _distributions(groups, RAW_FILE_PREFIX, fields, raw=True):
        wrapped["hasInput"] = {"@type": [RAW_DATA_TYPE, DATASET_TYPE], "dcat:distribution": raw_files}
    wrapped["hasOutput"] = _dataset_node(fields, groups, individuals, f"{test_type}Result")
    return wrapped


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
