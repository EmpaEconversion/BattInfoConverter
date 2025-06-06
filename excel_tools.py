"""
excel_tools.py
Drop-in replacement for ``pandas.read_excel`` that preserves the number of
decimal places shown in Excel cells.  All other behaviour (dates, strings,
formulas, etc.) is left untouched.

Usage
-----
from excel_tools import read_excel_preserve_decimals as read_excel
df = read_excel("file.xlsx", sheet_name="Data")
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, List, Sequence

import pandas as pd
from openpyxl import load_workbook


try:  # official location since openpyxl 3.1
    from openpyxl.utils.formatting import format_cell  # type: ignore
except ImportError:
    try:  # provisional path used by some wheels
        from openpyxl.utils.cell import format_cell  # type: ignore
    except ImportError:
        # Minimal fallback: respect only the number of decimals in the format
        def format_cell(cell) -> str:  # type: ignore
            val = cell.value
            if val is None:
                return ""

            fmt = getattr(cell, "number_format", "")
            if not isinstance(val, (int, float)) or "." not in fmt:
                return str(val)

            # count decimal places in the format, e.g. '0.000' → 3
            decs_fmt = fmt.split(".", 1)[1].split(";")[0]
            decs = sum(ch == "0" for ch in decs_fmt)
            return f"{val:.{decs}f}"


def _clean_cell(cell) -> Any:
    """Return a value that respects the cell’s displayed decimal places."""
    if cell.data_type != "n":  # not numeric
        return cell.value

    text = format_cell(cell)  # what Excel shows (might be scientific)
    if "E" in text or "e" in text:
        return cell.value  # keep scientific notation untouched

    if "." in text:  # count decimals and round accordingly
        n_dec = len(text.split(".", 1)[1])
        quant = Decimal(cell.value).quantize(
            Decimal("1." + "0" * n_dec), rounding=ROUND_HALF_UP
        )
        return float(quant)  # keep numeric type for downstream maths
    return cell.value  # integer-like or no decimal part


def read_excel_preserve_decimals(
    path: str,
    sheet_name: Any = 0,
    header: int | Sequence[int] | None = 0,
    **pd_kwargs,
) -> pd.DataFrame:
    """
    Load *path*/*sheet_name* into a pandas DataFrame while keeping the exact
    number of decimal places shown in Excel.

    All keyword arguments are forwarded to ``pd.DataFrame`` where meaningful.
    """
    wb = load_workbook(path, data_only=True)
    ws = wb[sheet_name] if isinstance(sheet_name, str) else wb.worksheets[sheet_name]

    # read every cell, cleaning numeric ones
    rows: List[List[Any]] = [[_clean_cell(c) for c in row] for row in ws.iter_rows()]

    df = pd.DataFrame(rows, **pd_kwargs)

    # Apply header logic similar to pandas.read_excel(header=0/None)
    if header is not None:
        df.columns = df.iloc[header]
        df = df.drop(index=list(range(header + 1))).reset_index(drop=True)

    return df
