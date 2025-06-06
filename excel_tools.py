"""
Utility loader that keeps the exact number of decimals a user sees in Excel,
circumventing pandas’ default loss of formatting information.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, List, Sequence

import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils.cell import format_cell


def _clean_cell(cell) -> Any:
    """Return a value that respects the cell’s number_format."""
    if cell.data_type != "n":                 # not numeric ➜ return as-is
        return cell.value

    text = format_cell(cell)                  # formatted string Excel shows
    if "E" in text or "e" in text:            # scientific notation → keep raw
        return cell.value

    if "." in text:                           # count decimals
        n_dec = len(text.split(".")[1])
        q = Decimal(cell.value).quantize(
            Decimal("1." + "0" * n_dec),
            rounding=ROUND_HALF_UP,
        )
        return float(q)                       # keeps downstream maths happy
    return cell.value                         # integer‐like


def read_excel_preserve_decimals(
    path: str,
    sheet_name: Any = 0,
    header: int | Sequence[int] | None = 0,
    **pd_kwargs,
) -> pd.DataFrame:
    """
    Drop-in replacement for ``pandas.read_excel`` that preserves Excel’s
    displayed decimal places.

    Parameters mirror ``pd.read_excel`` (unused kwargs are forwarded).
    """
    wb = load_workbook(path, data_only=True)
    ws = wb[sheet_name] if isinstance(sheet_name, str) else wb.worksheets[sheet_name]

    rows: List[list[Any]] = [
        [_clean_cell(c) for c in row]
        for row in ws.iter_rows(values_only=False)
    ]

    # hand off to pandas for headers, parsing, etc.
    return pd.DataFrame(rows).rename_axis(index=None).pipe(
        lambda df: pd.read_excel(         # reuse pandas parser for header logic
            pd.io.common.BytesIO(df.to_csv(index=False).encode()),
            header=header,
            **pd_kwargs,
        )
    )
