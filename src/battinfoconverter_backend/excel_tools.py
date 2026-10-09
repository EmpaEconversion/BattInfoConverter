"""Reading BattINFO Excel files.

Sheet and column names have changed across template versions, to keep backward
compatibility sheet names and columns are normalized on read.
"""

import logging
from pathlib import Path
from typing import IO

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.worksheet import Worksheet

logger = logging.getLogger(__name__)


# Sheet names have changed between template versions. Each canonical name is
# listed with alternative simplified spellings
# (lower case, no whitespace, no leading @)
SHEET_NAMES: dict[str, tuple[str, ...]] = {
    "@Schema": ("schema",),
    "@References": ("references",),
    "@Context": ("context", "context-toplevel"),
    "@Predicates": ("predicates", "context-connector"),
    "@Classes": ("classes", "uniqueid"),
    "@Individuals": ("individuals",),
    "@Units": ("units", "ontology-unit"),
}

# Sheets the conversion cannot run without
REQUIRED_SHEETS: tuple[str, ...] = ("@Schema", "@Context", "@Predicates", "@Units")

# @References is a label followed by a variable number of values
# Read as raw rows rather than as a pandas table
KEYED_ROW_SHEETS = frozenset({"@References"})

# Columns that are read, and so must resolve, on each sheet that is present
REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "@Schema": ("Metadata", "Value", "Unit", "Priority", "Ontology link"),
    "@Context": ("Term", "IRI"),
    "@Predicates": ("Predicate", "Default class"),
    "@Units": ("Unit", "Unit class"),
    "@Classes": ("Class",),
    "@Individuals": ("Name",),
}

# Column headers also changed, and the same heading means different things on
# different sheets, so they are resolved per sheet rather than across the book.
SHEET_COLUMNS: dict[str, dict[str, tuple[str, ...]]] = {
    "@Schema": {
        "Metadata": ("Metadata",),
        "Value": ("Value",),
        "Unit": ("Unit",),
        "Priority": ("Priority",),
        "Note": ("Note", "Comment"),
        "Ontology link": ("Ontology link",),
    },
    "@Context": {
        "Term": ("Term", "Item", "Prefix"),
        "IRI": ("IRI", "Key", "Namespace IRI"),
        "Note": ("Note",),
    },
    "@Predicates": {
        "Predicate": ("Predicate", "Item"),
        "Default class": ("Default class", "Default Class", "Key"),
        "Note": ("Note",),
    },
    "@Classes": {
        "Class": ("Class", "Item"),
        "IRI": ("IRI", "ID", "Class IRI"),
        "Note": ("Note",),
    },
    "@Individuals": {
        "Name": ("Name", "Item"),
        "Class": ("Class", "Type"),
        "IRI": ("IRI", "ID", "Class IRI"),
        "Note": ("Note",),
    },
    "@Units": {
        "Unit": ("Unit", "Item", "Symbol"),
        "Unit class": ("Unit class", "Unit IRI", "Key"),
        "Note": ("Note",),
    },
}

# Substrings to fall back on when no listed spelling matched, so unseen headings
# may still work. Only used for columns still missing, the narrower column is
# listed first so it gets first claim on a shared word.
COLUMN_KEYWORDS: dict[str, dict[str, tuple[str, ...]]] = {
    "@Schema": {"Note": ("note", "comment")},
    "@Context": {"IRI": ("iri", "namespace", "url"), "Term": ("term", "prefix", "name")},
    "@Predicates": {"Default class": ("class", "type"), "Predicate": ("predicate",)},
    "@Classes": {"IRI": ("iri",), "Class": ("class", "name")},
    "@Individuals": {"IRI": ("iri", "id"), "Class": ("class", "type"), "Name": ("name",)},
    "@Units": {"Unit class": ("class", "iri", "ontolog"), "Unit": ("unit", "symbol")},
}


def _normalize_columns(df: pd.DataFrame, sheet: str) -> pd.DataFrame:
    """Rename the columns of `sheet` to the canonical names for that sheet.

    Checks case insensitive SHEET_COLUMNS first, then the keyword fallback.
    """
    wanted = SHEET_COLUMNS.get(sheet)
    if not wanted:
        return df
    headings = {col: str(col).strip() for col in df.columns if isinstance(col, str)}
    renames: dict[str, str] = {}
    claimed: set[str] = set()

    for canonical, spellings in wanted.items():
        folded = {s.casefold() for s in spellings}
        for col, heading in headings.items():
            if col not in claimed and heading.casefold() in folded:
                renames[col] = canonical
                claimed.add(col)
                break

    for canonical, keywords in COLUMN_KEYWORDS.get(sheet, {}).items():
        if canonical in renames.values():
            continue
        for col, heading in headings.items():
            if col not in claimed and any(k in heading.casefold() for k in keywords):
                logger.debug("Reading '%s' of %s as '%s'", heading, sheet, canonical)
                renames[col] = canonical
                claimed.add(col)
                break

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


def _sheet_headings(excel_file: str | Path | IO[bytes] | Workbook) -> tuple[list[str], Workbook, bool]:
    """List the workbook's sheet names."""
    if isinstance(excel_file, Workbook):
        return list(excel_file.sheetnames), excel_file, False
    workbook = load_workbook(excel_file, read_only=True)
    return list(workbook.sheetnames), workbook, True


def _canonical_sheets(headings: list[str]) -> dict[str, str]:
    """Map canonical sheet names to the real sheet names in the Excel file."""
    # Map simplified sheet names to the real sheet names for comparing
    simple_headings = {h.replace(" ", "").lstrip("@").casefold(): h for h in headings}
    found = {}
    # If the simplified sheet name matches an accepted spelling, assign it to the canonical name
    for sheet, spellings in SHEET_NAMES.items():
        for spelling in spellings:
            match = simple_headings.get(spelling)
            if match:
                found[sheet] = match
                break
    return found


def _read_keyed_rows(ws: Worksheet) -> list[list]:
    """Read a sheet of label + variable-length value rows, dropping blank cells."""
    rows = []
    for row in ws.iter_rows(values_only=True):
        cells = [c.strip() if isinstance(c, str) else c for c in row]
        cells = [c for c in cells if c not in (None, "")]
        if cells:
            rows.append(cells)
    return rows


def _read_tables(
    excel_file: str | Path | IO[bytes] | Workbook,
    sheets: dict[str, str],
) -> dict[str, pd.DataFrame]:
    """Read every recognised table sheet, normalize columns."""
    wanted = {sheet: heading for sheet, heading in sheets.items() if sheet not in KEYED_ROW_SHEETS}
    if isinstance(excel_file, Workbook):
        frames = {}
        for sheet, heading in wanted.items():
            values = excel_file[heading].values
            frames[sheet] = pd.DataFrame(values, columns=next(values))
    else:
        parsed = pd.read_excel(excel_file, sheet_name=list(wanted.values()))
        frames = {sheet: parsed[heading] for sheet, heading in wanted.items()}

    tables = {}
    for sheet, frame in frames.items():
        df = _normalize_columns(_strip_df(frame), sheet)
        tables[sheet] = df.where(df.notna(), None)
    return tables


def _check_required(tables: dict[str, pd.DataFrame]) -> None:
    """Error message naming missing sheets and columns."""
    problems = [f"no {sheet} sheet" for sheet in REQUIRED_SHEETS if sheet not in tables]
    for sheet, columns in REQUIRED_COLUMNS.items():
        if (df := tables.get(sheet)) is None:
            continue
        if missing := [c for c in columns if c not in df.columns]:
            found = ", ".join(str(c) for c in df.columns)
            problems.append(f"{sheet} has no {' or '.join(missing)} column (found: {found})")
    if problems:
        msg = "Could not read the workbook: " + "; ".join(problems)
        raise KeyError(msg)


class ExcelContainer:
    """Wrapper for BattINFO Excel files.

    Abstracts Excel sheet name changes, loads data.
    """

    data: dict

    def __init__(self, excel_file: str | Path | IO[bytes] | Workbook) -> None:
        """Read all Excel sheets to dict of pandas dataframes."""
        headings, workbook, ours = _sheet_headings(excel_file)
        sheets = _canonical_sheets(headings)
        try:
            references = sheets.get("@References")
            extra_rows = _read_keyed_rows(workbook[references]) if references else None
        finally:
            if ours:
                workbook.close()

        tables = _read_tables(excel_file, sheets)
        _check_required(tables)

        schema = tables["@Schema"]
        units_df = tables["@Units"]
        context_toplevel = tables["@Context"]
        context_connector = tables["@Predicates"]
        unique_id = tables.get("@Classes")
        individuals = tables.get("@Individuals")

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
                if name := _cell(row, "Class"):
                    classes.add(name)
                    if iri := _cell(row, "IRI"):
                        unique_id_map[name] = iri

        # @Individuals names each individual's class and IRI outright
        individual_types: dict[str, str] = {}
        individual_names: set[str] = set()
        if individuals is not None:
            for _, row in individuals.iterrows():
                name = _cell(row, "Name")
                if not name:
                    continue
                individual_names.add(name)
                if iri := _cell(row, "IRI"):
                    unique_id_map[name] = iri
                if node_type := _cell(row, "Class"):
                    individual_types[name] = node_type

        if both := classes & individual_names:
            logger.warning(
                "%s listed on both @Classes and @Individuals, reading as individuals: %s",
                len(both),
                ", ".join(sorted(both)),
            )

        unit_map: dict[str, str] = {r["Unit"]: r["Unit class"] for _, r in units_df.iterrows()}

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
