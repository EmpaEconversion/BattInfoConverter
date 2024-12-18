import streamlit as st

markdown_content = """
# How to Fill Out the Excel Metadata File

- All the tabs present in the Excel file are essential for the web app. **Do not change their names**.
- The first row of each tab contains the column names. These are also used by the web app. **Do not change their names**.
- To fill in the metadata using our template file, simply fill in the data in the `Schema` tab and `Unique ID` tab.

### Schema Tab
This tab contains the majority of the metadata file.
- **Value**: Enter the metadata value. If the cell is empty, the script will skip this metadata item.
- **Unit**: Specify the unit of the metadata. If the metadata item doesn't require a unit, enter "No Unit." Leaving this cell blank will result in an error.
- **Ontology Link**: Provide the ontology link. If you do not want to ontologize a particular row, enter "NotOntologize." To add a comment instead, enter "Comment."

### Unique ID Tab
All unique string values (not numbers) are highly recommended to come with their own persistent unique identifier (online persistent unique identifier).
This includes the names of researchers or institutions. Please note that the chemical name itself is not unique.

For instance, Aluminium used in different battery cells is the same material by name but refers to distinct pieces.
We recommend simply assigning the correct ontology term to each chemical.

Unless the ontology link for that particular field is "Comment," BattInfo Converter will attempt to include the unique ID for every string value.
There are three scenarios in which the app will proceed:

__1) The item is listed in the "Item" column and its respective unique ID is listed in the "ID" column__
- This is for **Items with or without an Ontologized link but with a unique ID**.
- The app will add "@ID" along with its value in "@type" in the resulting JSON-LD file.

__2) The item is listed in the "Item" column but its respective unique ID is not listed in the "ID" column__
- This is for **Items with an Ontologized link but no unique ID**.
- Some items are ontologized but lack a unique ID. For example, "R2032," which is the name of a coin cell case, is listed in the BattInfo ontology but does not have a unique ID.
- The app will add this value in "@type" in the resulting JSON-LD file.

__3) The item is not listed at all in the Unique ID tab__
- This is for **Items with no Ontology link and no unique ID**.
- Some items lack a unique ID, such as the name of a newly-synthesized compound.
- The app will add this value in `rdfs:comment` in the resulting JSON-LD file.

"""
#####################################################################

st.markdown(markdown_content, unsafe_allow_html=True)

