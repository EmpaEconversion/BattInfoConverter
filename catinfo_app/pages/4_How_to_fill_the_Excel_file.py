import streamlit as st

st.title("How to fill the Excel file")

st.markdown(
    """
    - Most users should just have to modify the 'Value' column of the `@Schema` tab.
    - Additional ontology terms can be added in the `@Classes`, `@Individuals`, `@Units` and
      `@Context` tabs as needed.
    - Do not rename tabs or columns.
    """
)

st.subheader("The `@Schema` tab")

st.markdown(
    """
    This tab contains the majority of the metadata file.
    - **Value**: Enter the metadata value. If the cell is empty, the script will skip this metadata item.
    - **Unit**: Fill this in when the row is a quantity/measurement, using a symbol listed in the `@Units` tab.
      If the measurement is dimensionless, such as pH, use `unitless`.
      Leave the unit empty when the row is not a quantity/measurement (the legacy "No Unit" also works).
    - **Priority**: 'required', 'recommended' or 'optional'. This only decides whether you are warned
      when the value is missing.
    - **Note**: Your own remarks. This column is never converted.
    - **Ontology link**: Defines the path to the term in the JSON-LD. If you want to modify these,
      see the 'Modifying the template' page.
    """
)

st.subheader("How a 'Value' is interpreted")

st.markdown(
    """
    Values in the `@Schema` tab normally name an ontology class. The app works through the following
    steps in order, and stops at the first one that matches:

    __1) The value starts with `name|`, `label|` or `comment|`__
    - The rest of the cell is recorded as plain text, and no class is looked up.
    - Use this when something has no ontology class, for example `name|PVDF-HFP blend`.

    __2) The value is listed in the `@Individuals` tab__
    - The app writes the 'Class' column as `@type`, the 'IRI' column as `@id`, and the name as
      `schema:name`.

    __3) The value is listed in the `@Classes` tab__
    - The app writes it as `@type`.

    __4) The value is a term the context already knows__
    - The app writes it as `@type`, exactly as above. The `@Classes` tab is a convenience list of
      common options, not a restriction, so a class the ontology already knows works whether or not
      it is listed. The app knows terms from the
      [EMMO domain battery context](https://w3id.org/emmo/domain/battery/context).

    __5) None of the above__
    - The app writes the value in `rdfs:comment` and warns you, suggesting close matches where there
      are any.
    - If that is what you wanted, write `comment|` in front of the value to say so explicitly.
    - If it should be a class, check the spelling, add it to `@Classes`, or declare your own class in
      the `@Context` tab.
    """
)

st.subheader("The `@Individuals` tab")

st.markdown(
    """
    Individuals are specific, unique things, like people and organisations. as
    opposed to a class that can describe many things, like aluminium. There are
    three columns in the `@Individuals` tab:
    - **Name**: exactly what you type in the `@Schema` tab, for example `Empa`.
    - **Class**: ontology class for what it is, for example `schema:Person` or `schema:ResearchOrganization`.
    - **IRI**: a persistent identifier. We prefer an [ORCID](https://orcid.org) for a person, and a
      [Wikidata](https://www.wikidata.org) entity for an organisation.

    For Wikidata, use the entity form `http://www.wikidata.org/entity/Q683116` rather than the
    `/wiki/` page address.
    """
)

st.subheader("The `@References` tab")

st.markdown(
    """
    This tab adds metadata outside of the cell object.

    Enabling the sheet (putting `yes` for "Include references in metadata file") will change the
    structure of the output:

    **No references** - The Cell object is at the root

    **With references** - A 'Test' object is at the root, the Cell sits under 'hasTestObject', and
    references sit under 'hasOutput'.

    To fill in the sheet:
    - **Metadata**: the name of the field. Do not rename these, as the app matches them by name.
    - **Value**: the value for that field.
    - **Extra values**: what the remaining columns mean depends on the row.
        - After an author, they are that author's affiliations, one per column.
        - After a data file, the next column is a description of that file.
        - For a list such as the publication figures, every column is another item.
        - For everything else, only the 'Value' column is read.

    Rows ending in a capital letter, such as `Dataset authorA` and `Dataset authorB`, are collected
    into one list in the order of that letter. Add more by continuing the sequence.
    """
)

st.subheader("Going further")

st.markdown("If you want to add new units or entirely new metadata rows, see the next page:")

st.page_link("pages/5_Modifying_a_template.py", icon="➡️")
