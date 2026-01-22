import streamlit as st

markdown_content = """
# How to Adapt the Excel Metadata File for Your Own Custom Data

If you have your custom data schemas (you would like to change what to include in your metadata), you can simply modify our Excel metadata file to suit your custom data.

- You can add or remove existing rows in the `@Schema` tab to suit your data schemas.
- When new rows are added to the `@Schema` tab, please ensure to follow these steps:
- Depending on the template version, sheet names may be `@Schema`/`@Context`/`@Predicates`/`@Units`/`@Classes` or `Schema`/`@context-TopLevel`/`@context-Connector`/`Ontology - Unit`/`Unique ID`. The app accepts either naming convention.

#### 1. **Adding New Rows in the Metadata Column**
- The values in `Metadata`, `Type`, `Priority`, and `Comment` are not used by the web app and are therefore optional. You can fill in any name and information that best helps you manage the metadata file.

#### 2. **Adding New Ontology Terms**
- Ontology links are at the heart of ontologizing your metadata. Please ensure you use the proper ontology link here. Each level of the ontology link must be separated using `-`.
- The app will proceed through each of the ontology links separated by `-` to place the metadata value in the correct nested structure in the resulting JSON-LD.

    __Special Command:__
    - The app supports a special command in the ontology link, which can be specified using `|`. The list of possible special commands and their effects is as follows:
    - **"rev"**: The app will place the ontology link that starts with this special command (along with anything after this) in `"@reverse"`. For example: `-RatedCapacity-rev|hasInput`. Here, `hasInput` will be placed in `"@reverse"`.
    - **"type"**: The app will place the specific part in the Ontology link in `"@type"`. For example: `hasMeasuredProperty-type|RatedCapacity`, Rated Capacity will be placed in `"@type"` after `hasMeasuredProperty`.
    - If you are using BattInfo as your ontology concept, Dr. Simon Clark (simon.clark@sintef.no) will be delighted to assist you.

#### 3. **Multi-connectors with A/B/C Suffixes**
- If a connector repeats within the same parent (e.g., multiple solvents, solutes, additives, components), append a single capital letter to the connector name to control grouping and order: `hasSolventA`, `hasSolventB`, `hasComponentC`, etc.
- The suffix is an address: `A` maps to index 0, `B` to index 1, and so on. This works at any nesting level, including when the connector is the first segment (e.g., `hasComponentB-type|CatholyteCompartment-...`).
- The suffix is **not** kept in the output JSON-LD. The connector becomes `hasSolvent`/`hasComponent`, while the suffix only decides which list entry receives the value.

#### 4. **Adding Any Additional Ontology Top-Level**
- Sometimes, the appropriate ontology concept is not listed in the BattInfo ontology. You can use ontology concepts from other providers, such as `schema.org`. If this is the case, simply list your top-level ontology domain in the `@Context` tab.
- List the ontology shorthand and its respective link in the `Item` tab and `Key` tab, respectively.
- You can represent these ontology concepts from other sites using the notation `Ontology shorthand: Ontology concept`.
  - For example, the `comment` ontology is listed at https://www.w3.org/TR/rdf-schema/#ch_comment. We give `rdfs` as its shorthand. So, this can be represented as `rdfs:comment`.

#### 5. **List the Connector**
- Each of the ontology items in the `Ontology link` column in the `@Schema` tab that **is not the last one** is considered a connector and must be listed in the `@Predicates` tab.
- The items listed in the `Key` column are the "Default @type" for the listed ontology term. If the "Default @type" is listed, this type will be included in `"@type"` every time such a connector is used. This is optional, and not every connector has this "Default @type". For example:
  - `hasBinder`: has a default type of "Binder". Every time `hasBinder` is used, "Binder" will be added to `"@type"` of `hasBinder`.
  - `hasProperty`: has no default type.

#### 6. **Adding New Units**
- Add the unit in the `Unit` column in the `@Schema` tab.
- In the `@Units` tab, define the new unit. Include the `Item`, `Label`, and `Symbol` columns, along with the ontology reference in the `Key` column.

"""
#####################################################################

st.markdown(markdown_content, unsafe_allow_html=True)
