import streamlit as st

markdown_content = """

## Excel metadata files
Here you will find an Excel file template that you can fill out with your metadata
We will add more template for other cell types in the future. Be sure to check out!
### Blank Excel metadata file
[Coin cell battery schema version 1.0.0](https://github.com/user-attachments/files/18167520/Filled_BattinfoConverter_version1.0.xlsx) 
### Example filled out Excel metadata file
[Example-filled Coin cell battery schema version 1.0.0](https://github.com/user-attachments/files/18167522/Blank_BattinfoConverter_version1.0.xlsx)


"""
#####################################################################

st.markdown(markdown_content, unsafe_allow_html=True)


