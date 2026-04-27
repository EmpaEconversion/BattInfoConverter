"""Helper functions for Excel.

read_excel_preserve_decimals(): a drop-in replacement for pandas.read_excel
that *keeps the exact number of decimal places* a user sees in Excel.
"""

import logging
from collections.abc import Sequence
from pathlib import Path
from typing import IO, Any

import pandas as pd
from openpyxl import load_workbook
from openpyxl.cell.cell import Cell

logger = logging.getLogger(__name__)
# robust import for format_cell (new path / old path / fallback)
try:  # official since openpyxl 3.1
    from openpyxl.utils.formatting import format_cell
except ImportError:
    try:  # provisional path in some wheels
        from openpyxl.utils.cell import format_cell
    except ImportError:
        # very small local fallback
        def format_cell(cell: Cell) -> str:
            v = cell.value
            if v is None:
                return ""
            fmt = getattr(cell, "number_format", "")
            if not isinstance(v, (int, float)) or "." not in fmt:
                return str(v)
            decs = fmt.split(".", 1)[1].split(";")[0]
            n_dec = sum(ch == "0" for ch in decs)
            return f"{v:.{n_dec}f}"


def _clean_cell(cell: Cell) -> Any:
    """Return a value that respects the cell's displayed decimals."""
    if cell.data_type != "n":  # not numeric
        return cell.value

    shown = format_cell(cell)  # text Excel would display
    if "e" in shown.lower():  # scientific notation → leave as float
        return cell.value

    if "." in shown:  # count decimal places and round
        n_dec = len(shown.split(".", 1)[1])
        return round(float(cell.value), n_dec)
    return cell.value  # integer-like


def read_excel_preserve_decimals(
    path: str | Path | IO[bytes],
    sheet_name: str | int = 0,
    header: int | Sequence[int] | None = 0,
    **pd_kwargs: Any,
) -> pd.DataFrame:
    """Load an Excel sheet with pandas-style header and preserving decimal places.

    Keeps the same number of decimals as is visible in Excel.
    Reproduces pandas header logic (Unnamed columns + de-duplication).
    """
    wb = load_workbook(path, data_only=True)
    ws = wb[sheet_name] if isinstance(sheet_name, str) else wb.worksheets[sheet_name]

    # Read all rows, fixing numeric cells
    rows: list[list[Any]] = [[_clean_cell(c) for c in row] for row in ws.iter_rows()]

    # Build DataFrame without headers first
    df = pd.DataFrame(rows, **pd_kwargs)

    # Mimic pandas header behaviour
    if header is not None:
        hdr_row = df.iloc[header].tolist()

        # convert None → 'Unnamed: {i}', Decimal → str, then de-duplicate
        seen: dict[str, int] = {}
        clean_hdr: list[str] = []
        for i, col in enumerate(hdr_row):
            base = str(col) if col is not None else f"Unnamed: {i}"
            cnt = seen.get(base, 0)
            clean = base if cnt == 0 else f"{base}.{cnt}"
            seen[base] = cnt + 1
            clean_hdr.append(clean)

        df.columns = clean_hdr
        df = df.drop(index=list(range(header + 1))).reset_index(drop=True)

    return df


class ExcelContainer:
    """Wrapper for BattINFO Excel files.

    Abstracts Excel sheet name changes, loads data.
    """

    data: dict

    def __init__(self, excel_file: str | Path | IO[bytes]) -> None:
        """Read all Excel sheets to dict of pandas dataframes."""
        wb = load_workbook(excel_file, read_only=True)
        available_sheets = set(wb.sheetnames)
        wb.close()

        def _find_sheet(candidates: list[str]) -> pd.DataFrame:
            """Read the first sheet found in candidates to dataframe."""
            for name in candidates:
                if name in available_sheets:
                    return read_excel_preserve_decimals(excel_file, sheet_name=name)
            msg = f"None of {candidates} found in workbook"
            raise KeyError(msg)

        schema = _find_sheet(["@Schema", "Schema"])
        unit_map = _find_sheet(["@Units", "Ontology - Unit"])
        context_toplevel = _find_sheet(["@Context", "@context-TopLevel"])
        context_connector = _find_sheet(["@Predicates", "@context-Connector"])
        unique_id = _find_sheet(["@Classes", "Unique ID"])

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
                    "Missing %d/%d required values: %s",
                    sum(missing_mask),
                    sum(mask),
                    missing_vals_str,
                )

        unique_id_from_val: dict[str, str] = {r["Item"]: r["ID"] for _, r in unique_id.iterrows()}

        self.data = {
            "schema": schema,
            "unit_map": unit_map,
            "context_toplevel": context_toplevel,
            "context_connector": context_connector,
            "unique_id": unique_id,
            "unique_id_map": unique_id_from_val,
        }
