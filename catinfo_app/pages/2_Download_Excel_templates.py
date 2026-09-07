"""Downloads for Excel templates."""

import json
from io import BytesIO
from pathlib import Path

import streamlit as st

from battinfoconverter_backend.templates.template_conversion import (
    COINCELL_TEMPLATE_PATH,
    ELECTROLYSIS_TEMPLATE_PATH,
    FLOWCELL_TEMPLATE_PATH,
    dict_to_workbook,
)


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


coincell_xlsx_bytes, coincell_version = get_xlsx_bytes(COINCELL_TEMPLATE_PATH, empty=False)
coincell_xlsx_bytes_empty, _ = get_xlsx_bytes(COINCELL_TEMPLATE_PATH, empty=True)

flowcell_xlsx_bytes, flowcell_version = get_xlsx_bytes(FLOWCELL_TEMPLATE_PATH, empty=False)
flowcell_xlsx_bytes_empty, _ = get_xlsx_bytes(FLOWCELL_TEMPLATE_PATH, empty=True)

electrolysis_xlsx_bytes, electrolysis_version = get_xlsx_bytes(ELECTROLYSIS_TEMPLATE_PATH, empty=False)
electrolysis_xlsx_bytes_empty, _ = get_xlsx_bytes(ELECTROLYSIS_TEMPLATE_PATH, empty=True)

st.title("Download Excel templates")
st.text("Here you will find Excel templates that you can fill out with your metadata.")

st.subheader("Electrolysis cell")
st.download_button(
    label=f"⬇️ Electrolysis cell template v{electrolysis_version} - empty",
    data=electrolysis_xlsx_bytes_empty,
    file_name=f"CatINFO_electrolysis_v{electrolysis_version}_empty.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
st.download_button(
    label=f"⬇️ Electrolysis cell template v{electrolysis_version} - filled example",
    data=electrolysis_xlsx_bytes,
    file_name=f"CatINFO_electrolysis_v{electrolysis_version}_filled.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

st.subheader("Coin cell")
st.download_button(
    label=f"⬇️ Coin cell battery template v{coincell_version} - empty",
    data=coincell_xlsx_bytes_empty,
    file_name=f"BattINFO_coincell_v{coincell_version}_empty.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
st.download_button(
    label=f"⬇️ Coin cell battery template v{coincell_version} - filled example",
    data=coincell_xlsx_bytes,
    file_name=f"BattINFO_coincell_v{coincell_version}_filled.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

st.subheader("Redox flow battery cell")
st.download_button(
    label=f"⬇️ Redox flow cell template v{flowcell_version} - empty",
    data=flowcell_xlsx_bytes_empty,
    file_name=f"BattINFO_flowcell_v{flowcell_version}_empty.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
st.download_button(
    label=f"⬇️ Redox flow cell template v{flowcell_version} - filled example",
    data=flowcell_xlsx_bytes,
    file_name=f"BattINFO_flowcell_v{flowcell_version}_filled.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
