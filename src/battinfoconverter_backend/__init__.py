"""Backend utilities for the BattINFO converter."""

from . import auxiliary, excel_tools, json_convert, json_template

__all__ = [
    "auxiliary",
    "excel_tools",
    "json_convert",
    "json_template",
]

__version__ = getattr(json_convert, "APP_VERSION", "0.0.0")
