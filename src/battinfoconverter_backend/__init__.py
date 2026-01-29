"""Backend utilities for the BattINFO converter."""

from importlib.metadata import version

from . import auxiliary, excel_tools, json_convert, json_template

__all__ = [
    "auxiliary",
    "excel_tools",
    "json_convert",
    "json_template",
]

__version__ = version("battinfoconverter-backend")
