import streamlit as st

markdown_content = """

## Excel metadata files
Here you will find an Excel file template that you can fill out with your metadata
We will add more template for other cell types in the future. Be sure to check out!

Please note that the empty file cannot be submitted to conversion directly as the blank file lacks 4 required fields: CellID, Date of cell assembly, Institution/company and Scientist/technician/operator.
These fields are needed to be filled before the file can be subjected to the conversion. 


### Blank Excel metadata template file
[Coin cell battery template version 1.1.2](https://github.com/EmpaEconversion/BattInfoConverter/raw/main/Excel%20for%20reference/Battery2030%2B_CoinCellBattery_Schema_Ontologized_1.1.2_Empty.xlsx) 
### Example filled Excel metadata template file
[Example-filled coin cell battery template version 1.1.2](https://github.com/EmpaEconversion/BattInfoConverter/raw/main/Excel%20for%20reference/250515_241125_Battery2030%2B_CoinCellBattery_Schema_Ontologized_1.1.2_filled.xlsx)


"""
#####################################################################

st.markdown(markdown_content, unsafe_allow_html=True)


