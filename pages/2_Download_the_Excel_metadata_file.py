import streamlit as st

markdown_content = """

## Excel metadata files
Here you will find Excel templates that you can fill out with your metadata.
We will add more template for other cell types in the future. Be sure to check them out!

Please note that the empty file cannot be submitted to conversion directly as the blank file lacks 4 required fields: CellID, Date of cell assembly, Institution/company and Scientist/technician/operator.
These fields must be filled before the file can be sbmitted for conversion. 


### Blank Excel metadata template file
[Coin cell battery template version 1.1.15](https://github.com/EmpaEconversion/BattInfoConverter/raw/refs/heads/development/Excel%20for%20reference//BattINFOconverter_CoinCell_template_version_1.1.15_empty.xlsx) 
### Example filled Excel metadata template file
[Example-filled coin cell battery template version 1.1.15](https://github.com/EmpaEconversion/BattInfoConverter/raw/refs/heads/development/Excel%20for%20reference/BattINFOconverter_CoinCell_template_version_1.1.15_filled.xlsx)


"""
#####################################################################

st.markdown(markdown_content, unsafe_allow_html=True)


