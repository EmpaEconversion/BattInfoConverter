"""Helper functions for Excel.

read_excel_preserve_decimals(): a drop-in replacement for pandas.read_excel
that *keeps the exact number of decimal places* a user sees in Excel.
"""

import logging
from pathlib import Path
from typing import IO

import pandas as pd
from openpyxl import Workbook, load_workbook

logger = logging.getLogger(__name__)


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
    return df.where(df.notna(), None)


class ExcelContainer:
    """Wrapper for BattINFO Excel files.

    Abstracts Excel sheet name changes, loads data.
    """

    data: dict

    def __init__(self, excel_file: str | Path | IO[bytes] | Workbook) -> None:
        """Read all Excel sheets to dict of pandas dataframes."""
        wb = excel_file if isinstance(excel_file, Workbook) else load_workbook(excel_file, read_only=True)
        available_sheets = set(wb.sheetnames)
        wb.close()

        def _find_sheet(candidates: list[str]) -> pd.DataFrame:
            """Read the first sheet found in candidates to dataframe."""
            for name in candidates:
                if name in available_sheets:
                    return _read_excel_or_wb(excel_file, name)
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
                    "%sMissing %d/%d %s values: %s",
                    "IMPORTANT: " if priority == "required" else "",
                    sum(missing_mask),
                    sum(mask),
                    priority,
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
