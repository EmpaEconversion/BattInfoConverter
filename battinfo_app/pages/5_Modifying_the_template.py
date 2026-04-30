import streamlit as st

markdown_content = """
If you have your custom data schemas (you would like to change what to include in your metadata), you can simply modify
our Excel metadata file to suit your custom data.

#### 1. **Adding New Rows @Schema**
- 'Metadata' is the key, describing the term to your users
- 'Value' is the ontologized term or number/string value that is put in the JSON-LD
- 'Unit' should be a valid unit listed in the `@Units` tab, or 'No Unit'
- 'Priority' can be 'required', 'recommended', 'optional', and only determines if a user is warned when a term is missing.
- 'Ontology link' defines how the term is placed into the JSON-LD structure.

#### 2. **Creating an ontology link**
- Ontology links are at the heart of ontologizing your metadata. Please ensure you use the proper ontology link here. Each level of the ontology link must be separated using `-`.
- The app will proceed through each of the ontology links separated by `-` to place the metadata value in the correct nested structure in the resulting JSON-LD.

    __Special Command:__
    Terms starting with a special command will have special effects:
    - **"rev|"**: The app will place the ontology link that starts with this special command (along with anything after this) in `"@reverse"`. For example: `-RatedCapacity-rev|hasInput`. Here, `hasInput` will be placed in `"@reverse"`.
    - **"type|"**: The app will place the specific part in the Ontology link in `"@type"`. For example: `hasMeasuredProperty-type|RatedCapacity`, Rated Capacity will be placed in `"@type"` after `hasMeasuredProperty`.

#### 3. **Multi-connectors with A/B/C Suffixes**
- If a connector repeats within the same parent (e.g., multiple solvents, solutes, additives, components), append a single capital letter to the connector name to control grouping and order: `hasSolventA`, `hasSolventB`, `hasComponentC`, etc.
- This works at any nesting level, including when the connector is the first segment (e.g., `hasComponentB-type|CatholyteCompartment-...`).
- The suffix is **not** kept in the output JSON-LD. The connector becomes `hasSolvent`/`hasComponent`, while the suffix only decides which list entry receives the value.

#### 4. **Adding Any Additional Ontology Terms**

- We use the [BattINFO ontology] as the default namespace. Currently, to use a term from the default namespace, it must be added to the `@Classes` tab (it does not need its IRI).
- We have additional namespaces in the `@Context`, like "schema" pointing to "https://schema.org/". You can add and use more namespaces here.
- Terms with an IRI not included in any namespace, such as people, companies, or niche concepts, can be added to the `@Classes` with their IRI.

#### 5. **Default types for predicates**
- Relationships between terms are defined with subject → predicate → object.
- Predicates usually start with `has`, e.g. `hasProperty`, `hasCoating` etc..
- The `@Predicates` tab allows us to assign a default `@type` to the object.
- e.g. `hasBinder` has a default `@type` of `Binder`. Every time `hasBinder` is used, the object will have `{"@type": "Binder"}`.
- `hasMeasuredProperty`: has no default type, but it can be defined in the ontology link with e.g. `type|Thickness`.

#### 6. **Adding New Units**
- In the `@Units` tab, add a shorthand in the 'Item' column and the IRI or a term that expands to an IRI in the 'Key' column.
- The shorthand can now be used in the 'Unit' column of the `@Schema` tab.

"""
#####################################################################

st.markdown(markdown_content, unsafe_allow_html=True)
