"""Backend utilities for the BattINFO converter."""

from importlib.metadata import version

from . import auxiliary, excel_tools, json_convert, json_template
from .json_convert import convert_excel_to_jsonld

__all__ = [
    "auxiliary",
    "convert_excel_to_jsonld",
    "excel_tools",
    "json_convert",
    "json_template",
]

__version__ = version("battinfoconverter-backend")
