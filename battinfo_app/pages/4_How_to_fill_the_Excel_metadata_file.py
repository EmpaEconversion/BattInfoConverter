import streamlit as st

st.title("How to fill the Excel metadata file")

st.markdown(
    """
    - Most users should just have to modify the 'Value' column of the `@Schema` tab.
    - Additional ontology terms can be added in the `@Units`, and `@Classes` tab as needed.
    - Do not change tab names or column names in the file - they are essential for the web app.
    """
)

st.subheader("The `@Schema` tab")

st.markdown(
    """
    This tab contains the majority of the metadata file.
    - **Value**: Enter the metadata value. If the cell is empty, the script will skip this metadata item.
    - **Unit**: Specify the unit of the metadata. If the metadata item does not require a unit, enter "No Unit."
      Leaving this cell blank will result in an error.
    - **Ontology Link**: The ontology link defines the path to the term in the JSON-LD. If you want to modify these,
      see the 'Modifying the template' page.
    """
)

st.subheader("Adding terms to `@Classes`")

st.markdown(
    """
    Inputs to the 'Value' column of the `@Schema` tab should point to an IRI, or be a literal value.

    All terms that point to an IRI should be listed in the `@Classes` tab.

    When adding a term from the Excel to the JSON-LD, there are four ways for the app to proceed:

    __1) The item is in `@Classes` with a unique ID__
    - The app will add the 'item' as its `@type`, and the 'ID' as the `@id` in the resulting JSON-LD file.

    __2) The item is in `@Classes` with a unique ID and is a creator or manufacturer__
    - The app will add the 'item' as its `schema:name`, and the 'ID' as the `@id` in the resulting JSON-LD file.

    __3) The item is in `@Classes` without a unique ID__
    - The term is already in the default context, so an IRI does not need to be provided.
    - The app will add this value in "@type" in the resulting JSON-LD file.

    __4) The item is not listed at all in the @Classes tab__
    - The app will add this value in `rdfs:comment` in the resulting JSON-LD file, and warn the user.
    - If the intended behaviour is to add a comment, put "rdfs:comment" at the end of the ontology link.
    - If the term is intended to point to an IRI, add it to the `@Classes` tab.
    """
)

st.subheader("Going further")

st.markdown("If you want to add new units or entirely new metadata rows, see the next page:")

st.page_link("pages/5_Modifying_the_template.py", icon="➡️")
