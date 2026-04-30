import streamlit as st

markdown_content = """
# How to fill the Excel metadata file

- Most users should just have to modify the 'Value' column of the `@Schema` tab.
- Additional ontology terms can be added in the `@Predicates`, `@Units`, and `@Classes` tab as needed.
- Do not change tab names or column names in the file - they are essential for the web app.

### @Schema Tab
This tab contains the majority of the metadata file.
- **Value**: Enter the metadata value. If the cell is empty, the script will skip this metadata item.
- **Unit**: Specify the unit of the metadata. If the metadata item does not require a unit, enter "No Unit." Leaving this cell blank will result in an error.
- **Ontology Link**: The ontology link defines the path to the term in the JSON-LD. If you want to modify these, see the 'Modifying the template' page.

### Values in @Schema

Inputs to the 'Value' column of the `@Schema` tab should point to an IRI, or be a literal value.

All terms that point to an IRI should be listed in the `@Classes` tab.

When adding a term from the Excel to the JSON-LD, there are three ways for the app to proceed:

__1) The item is in `@Classes` with a unique ID__
- The app will add the 'item' as its `@type`, and the 'ID' as the `@id` in the resulting JSON-LD file.

__1) The item is in `@Classes` with a unique ID and is a creator or manufacturer__
- The app will add the 'item' as its `schema:name`, and the 'ID' as the `@id` in the resulting JSON-LD file.

__2) The item is in `@Classes` without a unique ID__
- The term is already in the default context, so an IRI does not need to be provided.
- The app will add this value in "@type" in the resulting JSON-LD file.

__3) The item is not listed at all in the @Classes tab__
- The app will add this value in `rdfs:comment` in the resulting JSON-LD file, and warn the user.
- If the intended behaviour is to add a comment, please explicitly put "rdfs:comment" at the end of the ontology link.
- If the term is intended to point to an IRI, add it to the `@Classes` tab.

"""
#####################################################################

st.markdown(markdown_content, unsafe_allow_html=True)
