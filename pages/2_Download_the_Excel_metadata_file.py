import streamlit as st

markdown_content = """

## Excel metadata files
Here you will find an Excel file template that you can fill out with your metadata
We will add more template for other cell types in the future. Be sure to check out!
### Blank Excel metadata file
[Coin cell battery schema version 1.0.0](https://github.com/user-attachments/files/19011470/241125_Battery2030%2B_CoinCellBattery_Schema_Ontologized_1.0.0_blank.xlsx) 
### Example filled out Excel metadata file
[Example-filled Coin cell battery schema version 1.0.0](https://github.com/user-attachments/files/19026928/241125_Battery2030%2B_CoinCellBattery_Schema_Ontologized_1.0.0_filled.xlsx)


"""
#####################################################################

st.markdown(markdown_content, unsafe_allow_html=True)


