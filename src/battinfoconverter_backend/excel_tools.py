"""Helper functions for Excel.

read_excel_preserve_decimals(): a drop-in replacement for pandas.read_excel
that *keeps the exact number of decimal places* a user sees in Excel.
"""

import logging
from pathlib import Path
from typing import IO

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.worksheet import Worksheet

logger = logging.getLogger(__name__)


# Column headers differ between template versions, map them to the names used downstream
COLUMN_ALIASES = {
    "Class": "Item",
    "Predicate": "Item",
    "Default Class": "Key",
}

# Headers whose wording varies, matched by their start
COLUMN_PREFIX_ALIASES = {"Class IRI": "ID"}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename the columns of a sheet to the canonical names."""
    renames = {}
    for col in df.columns:
        if not isinstance(col, str):
            continue
        alias = COLUMN_ALIASES.get(col)
        if alias is None:
            alias = next((v for k, v in COLUMN_PREFIX_ALIASES.items() if col.startswith(k)), None)
        if alias is not None and alias not in df.columns:
            renames[col] = alias
    return df.rename(columns=renames)


def _cell(row: pd.Series, *names: str) -> str | None:
    """Read the first of `names` the row actually has a value for.

    Column headers have been renamed across template versions, so a sheet is read
    by trying each spelling in turn.
    """
    for name in names:
        value = row.get(name)
        if value is not None and not pd.isna(value) and str(value).strip():
            return str(value).strip()
    return None


def _strip_df(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace from all string values and column names."""
    df.columns = df.columns.str.strip()
    return df.apply(lambda col: col.map(lambda x: x.strip() if isinstance(x, str) else x))


def _read_excel_or_wb(
    excel_file: str | Path | IO[bytes] | Workbook,
    sheet_name: str,
) -> pd.DataFrame:
    """Load an Excel sheet from file or workbook, replaces NaN with None."""
    if isinstance(excel_file, Workbook):
        data = excel_file[sheet_name].values
        headers = next(data)
        df = pd.DataFrame(data, columns=headers)
    else:
        df = pd.read_excel(excel_file, sheet_name)
    df = _normalize_columns(_strip_df(df))
    return df.where(df.notna(), None)


def _read_extra_rows(ws: Worksheet) -> list[list]:
    """Read a sheet of label + variable-length value rows, dropping blank cells."""
    rows = []
    for row in ws.iter_rows(values_only=True):
        cells = [c.strip() if isinstance(c, str) else c for c in row]
        cells = [c for c in cells if c not in (None, "")]
        if cells:
            rows.append(cells)
    return rows


class ExcelContainer:
    """Wrapper for BattINFO Excel files.

    Abstracts Excel sheet name changes, loads data.
    """

    data: dict

    def __init__(self, excel_file: str | Path | IO[bytes] | Workbook) -> None:
        """Read all Excel sheets to dict of pandas dataframes."""
        wb = excel_file if isinstance(excel_file, Workbook) else load_workbook(excel_file, read_only=True)
        available_sheets = set(wb.sheetnames)
        extra_rows = _read_extra_rows(wb["@References"]) if "@References" in available_sheets else None
        wb.close()

        def _optional_sheet(candidates: list[str]) -> pd.DataFrame | None:
            """Read the first sheet found in candidates, None if the workbook has none."""
            for name in candidates:
                if name in available_sheets:
                    return _read_excel_or_wb(excel_file, name)
            return None

        def _find_sheet(candidates: list[str]) -> pd.DataFrame:
            """Read the first sheet found in candidates to dataframe."""
            found = _optional_sheet(candidates)
            if found is None:
                msg = f"None of {candidates} found in workbook"
                raise KeyError(msg)
            return found

        schema = _find_sheet(["@Schema", "Schema"])
        units_df = _find_sheet(["@Units", "Ontology - Unit"])
        context_toplevel = _find_sheet(["@Context", "@context-TopLevel"])
        context_connector = _find_sheet(["@Predicates", "@context-Connector"])
        unique_id = _optional_sheet(["@Classes", "Unique ID"])
        individuals = _optional_sheet(["@Individuals"])

        # Log missing required, recommended, and optional terms
        for priority, loggerfunc in (
            ("required", logger.critical),
            ("recommended", logger.warning),
        ):
            mask = schema["Priority"] == priority
            missing_mask = schema[mask]["Value"].isna()
            if any(missing_mask):
                missing_vals = schema[mask][missing_mask]["Metadata"].to_list()
                missing_vals_str = ", ".join(["'" + f + "'" for f in missing_vals])
                loggerfunc(
                    "%sMissing %d/%d %s values: %s",
                    "IMPORTANT: " if priority == "required" else "",
                    sum(missing_mask),
                    sum(mask),
                    priority,
                    missing_vals_str,
                )

        # @Classes lists the classes available in the Value column. Older sheets
        # also carried an IRI per row, which made that value a named individual.
        classes: set[str] = set()
        unique_id_map: dict[str, str] = {}
        if unique_id is not None:
            for _, row in unique_id.iterrows():
                if name := _cell(row, "Item", "Class", "Name"):
                    classes.add(name)
                    if iri := _cell(row, "ID", "IRI"):
                        unique_id_map[name] = iri

        # @Individuals names each individual's class and IRI outright
        individual_types: dict[str, str] = {}
        individual_names: set[str] = set()
        if individuals is not None:
            for _, row in individuals.iterrows():
                name = _cell(row, "Name", "Item")
                if not name:
                    continue
                individual_names.add(name)
                if iri := _cell(row, "IRI", "ID"):
                    unique_id_map[name] = iri
                if node_type := _cell(row, "Type"):
                    individual_types[name] = node_type

        if both := classes & individual_names:
            logger.warning(
                "%s listed on both @Classes and @Individuals, reading as individuals: %s",
                len(both),
                ", ".join(sorted(both)),
            )

        unit_map: dict[str, str] = {r["Item"]: r["Key"] for _, r in units_df.iterrows()}

        self.data = {
            "schema": schema,
            "unit_map": unit_map,
            "context_toplevel": context_toplevel,
            "context_connector": context_connector,
            "unique_id": unique_id,
            "unique_id_map": unique_id_map,
            "classes": classes,
            "individuals": individuals,
            "individual_names": individual_names,
            "individual_types": individual_types,
            "extra_rows": extra_rows,
        }
