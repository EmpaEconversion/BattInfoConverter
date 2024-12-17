import streamlit as st

markdown_content = """
# How to Fill Out the Excel Metadata File

- All the tabs present in the Excel file are essential for the web app. **Do not change their names**.
- The first row of each tab contains the column names. These are also used by the web app. **Do not change their names**.
- To fill in the metadata using our template file, simply fill in the data in the `JSON - Info` tab, `Schema` tab, and `Unique ID` tab.

### JSON - Info Tab
This tab contains the information that is displayed at the top level of the JSON-LD file. The logic for representing this information is slightly different from the one in the `Schema` tab. Hence, they are placed in a different tab. Simply fill in the value in the `Key` column.

### Schema Tab
This tab contains the majority of the metadata file.
- **Value**: Enter the metadata value. If the cell is empty, the script will skip this metadata item.
- **Unit**: Specify the unit of the metadata. If the metadata item doesn't require a unit, enter "No Unit." Leaving this cell empty will cause an error.
- **Ontology Link**: Provide the ontology link. If you do not want to ontologize a particular row, enter "NotOntologize." To add a comment instead, enter "Comment."

### Unique ID Tab
All unique string values (not numbers) are highly recommended to come with their own unique identifier (online unique identifier).
These includes name of the reserachers or institution. Please note that the chemical name is not uniqe. For example, Aluminium that is put in each cell are not unique.
Although they are Aluminium, they are different piece. We recommend to simply put the correct ontology term to each chemical.
Unless the ontology link for that particular field is "Comment," BattInfo Converter will attempt to include the unique ID for every string value.
There are three scenarios in which the app will proceed:

__1) The item is listed in the "Item" column and its respective unique ID is listed in the "ID" column__
- This is for **Items with or without Ontologized link but with a unique ID**.
- The app will add "@ID" along with its value in "@type" in the resulting JSON-LD file.

__2) The item is listed in the "Item" column but its respective unique ID is not listed in the "ID" column__
- This is for **Items with Ontologized link but no unique ID**.
- Certain items are ontologized but do not have a unique ID. For example, "R2032," which is the name of a coin cell case, is listed in the BattInfo ontology but does not have a unique ID.
- The app will add this value in "@type" in the resulting JSON-LD file.

__3) The item is not listed at all in the Unique ID tab__
- This is for **Items with no Ontology link and no unique ID**.
- Some items do not have a unique ID. For example, a chemical name of a newly-synthesized compound.
- The app will add this value in `rdfs:comment` in the resulting JSON-LD file.

"""
#####################################################################

st.markdown(markdown_content, unsafe_allow_html=True)


