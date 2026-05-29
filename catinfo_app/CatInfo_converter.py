"""Streamlit web app interface."""

import logging
from collections.abc import Generator
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path

import simplejson as json
import streamlit as st

from battinfoconverter_backend import __version__
from battinfoconverter_backend.json_convert import convert_excel_to_jsonld


# Catch warnings emitted by logging, for displaying nicely in streamlit
class _CollectWarnings(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.records: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record.getMessage())


@contextmanager
def collect_warnings(logger_name: str = "battinfoconverter_backend") -> Generator[list[str], None, None]:
    """Context manager, grabs warnings, returns as list."""
    handler = _CollectWarnings()
    logger = logging.getLogger(logger_name)
    logger.addHandler(handler)
    try:
        yield handler.records
    finally:
        logger.removeHandler(handler)


st.set_page_config(
    page_title="CatINFO Converter",
    page_icon="catinfo_app/assets/catinfo-logo-only.svg",
    layout="centered",
)

badge_url = "https://visitor-badge.laobi.icu/badge?page_id=catinfoconverter.streamlit.app"
st.image(badge_url)

markdown_content = """
### Overview
CatINFO converter helps you ontologize battery cell metadata using the
[EMMO](https://emmo-repo.github.io/)
[domain-battery ontology](https://emmo-repo.github.io/domain-battery/),
improving data interoperability across platforms and research groups.
In practice, ontologizing metadata can be complex and tedious, so we developed this open-source
web application to streamline and simplify the process.

CatINFO converter converts a user-fillable Excel file into a fully ontologized JSON-LD file.
Templates are provided for electrolysis cells and coin cell batteries.
Most users can fill the Excel, drag and drop the file here, and get an ontologized JSON-LD.

Advanced users can modify the Excel templates for their teams, and we also provide the backend
powering this app as a standalone pip-installable Python package with
`pip install battinfoconverter-backend`.
For problems and suggestions, please make an issue in our [GitHub: BattINFO
converter](https://github.com/EmpaEconversion/BattInfoConverter) page.

### Acknowledgement
The CatINFO converter web application was developed by Graham Kimbell, Nukorn Plainpan, and Prof.
Corsin Battaglia at [Empa](https://www.empa.ch/), the Swiss Federal Laboratories for Materials
Science and Technology in the Laboratory
[Materials for Energy Conversion](https://www.empa.ch/web/s501), with support from Simon Clark
(SINTEF). The app is based on [BattINFO converter](https://battinfoconverter.streamlit.app), using
the [same backend](https://github.com/empaeconversion/battinfoconverter).
The development of CatINFO converter was supported by funding from the
[PREMISE](https://ord-premise.org/) project from the open research data program of the ETH Board.

### Citation
Nukorn Plainpan, Simon Clark, and Corsin Battaglia. "BattINFO Converter: An Automated Tool for
Semantic Annotation of Battery Cell Metadata." *Batteries & Supercaps* (**2025**): 2500151.
[doi.org/10.1002/batt.202500151](https://doi.org/10.1002/batt.202500151)
"""


def main() -> None:
    """Define layout of app."""
    st.image("catinfo_app/assets/catinfo-long.svg", width=700)

    st.markdown(f"__App Version: {__version__}__")

    uploaded_file = st.file_uploader("__Upload your metadata Excel file here__", type=["xlsx", "xlsm"])

    if uploaded_file is not None:
        # Get stem of file
        base_name = Path(uploaded_file.name).stem

        # Convert the uploaded Excel file to JSON-LD
        with collect_warnings() as warnings:
            jsonld_output = convert_excel_to_jsonld(uploaded_file, validate=True)
        jsonld_str = json.dumps(jsonld_output, indent=4, use_decimal=True)

        if warnings:
            st.warning(
                f"**{len(warnings)} Warning{'' if len(warnings) == 1 else 's'}**  \n  \n"
                + "  \n".join(["- " + w for w in warnings])
            )

        jsonld_str = json.dumps(jsonld_output, indent=4, use_decimal=True)

        # Download button
        to_download = BytesIO(jsonld_str.encode())
        output_file_name = f"CatINFO_converter_{base_name}.json"
        st.download_button(
            label="Download JSON-LD",
            data=to_download,
            file_name=output_file_name,
            mime="application/json",
        )

        # Convert JSON-LD output to a string to display in text area (for preview)
        st.code(jsonld_str, height=1000, language="json")

    st.markdown(markdown_content, unsafe_allow_html=True)
    st.image("./catinfo_app/assets/sponsor.png", width=700)


if __name__ == "__main__":
    main()
