"""Downloads for excel templates."""

import json
from io import BytesIO
from pathlib import Path

import streamlit as st

from battinfoconverter_backend.templates.template_conversion import COINCELL_TEMPLATE_PATH, dict_to_workbook


@st.cache_data
def get_xlsx_bytes(schema_path: Path, *, empty: bool) -> tuple[bytes, str]:
    """Create xlsx bytes object, and get version."""
    with schema_path.open("r") as f:
        data = json.load(f)
    version = next(
        (
            c["Value"]
            for c in data["@Schema"]["data"]["Cell identification"]["rows"]
            if c["Metadata"] == "Schema version"
        ),
        "0.0.0",
    )
    wb = dict_to_workbook(data, empty=empty)
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue(), version


xlsx_bytes, version = get_xlsx_bytes(COINCELL_TEMPLATE_PATH, empty=False)
xlsx_bytes_empty, _ = get_xlsx_bytes(COINCELL_TEMPLATE_PATH, empty=True)

st.title("Download the Excel metadata file")
st.text("Here you will find Excel templates that you can fill out with your metadata.")
st.subheader("Excel template files")
st.download_button(
    label=f"⬇️ Coin cell battery template v{version} - empty",
    data=xlsx_bytes_empty,
    file_name=f"BattINFO_converter_standard_Excel_version_{version}_empty.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
st.download_button(
    label=f"⬇️ Coin cell battery template v{version} - filled example",
    data=xlsx_bytes,
    file_name=f"BattINFO_converter_standard_Excel_version_{version}_filled.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
