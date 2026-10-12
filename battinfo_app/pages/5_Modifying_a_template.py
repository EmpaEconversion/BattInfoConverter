import streamlit as st

st.title("Modifying a template")
st.markdown(
    """
    To change what metadata is included in the output JSON-LD, you can modify an Excel template file.
    """
)

st.subheader("1. Adding new rows to `@Schema`")

st.markdown(
    """
    - 'Metadata' is the key, describing the term to your users
    - 'Value' is the ontologized term or number/string value that is put in the JSON-LD
    - 'Unit' should be a unit listed in the `@Units` tab when the row is a measurement, and empty
      when it is not. Use `unitless` for a dimensionless measurement such as pH.
    - 'Priority' can be 'required', 'recommended', or 'optional', and only determines if a user is
      warned when a term is missing.
    - 'Note' is for your own remarks and is never converted.
    - 'Ontology link' defines how the term is placed into the JSON-LD structure.
    """
)

st.subheader("  1.1. Creating an ontology link")

st.markdown(
    """
    - Ontology links are at the heart of ontologizing your metadata. Please ensure you use the proper ontology link
      here. Each level of the ontology link must be separated using `-`.
    - The app will proceed through each of the ontology links separated by `-` to place the metadata value in the
      correct nested structure in the resulting JSON-LD.

        __Special Command:__
        Terms starting with a special command will have special effects:
        - **"rev|"**: The app will place the ontology link that starts with this special command (along with anything
        after this) in `"@reverse"`. For example: `-RatedCapacity-rev|hasInput`. Here, `hasInput` will be placed in
        `"@reverse"`.
        - **"type|"**: The app will place the specific part in the Ontology link in `"@type"`. For example:
        `hasMeasuredProperty-type|RatedCapacity`, Rated Capacity will be placed in `"@type"` after
        `hasMeasuredProperty`.
    """
)

st.subheader("  1.2 Multi-connectors with A/B/C Suffixes")

st.markdown(
    """
    - If a connector repeats within the same parent (e.g., multiple solvents, solutes, additives, components), append a
      single capital letter to the connector name to control grouping and order: `hasSolventA`, `hasSolventB`,
      `hasComponentC`, etc.
    - This works at any nesting level, including when the connector is the first segment (e.g.,
      `hasComponentB-type|CatholyteCompartment-...`).
    - The suffix is **not** kept in the output JSON-LD. The connector becomes `hasSolvent`/`hasComponent`, while the
      suffix only decides which list entry receives the value.
    """
)

st.subheader("2. Adding namespaces and your own classes to `@Context`")

st.markdown(
    """
    - We use the [BattINFO ontology](https://w3id.org/emmo/domain/battery/context) as the default namespace.
    - The `@Context` tab holds a 'Term' and the 'IRI' it stands for, e.g. `schema` and
      `https://schema.org/`.
    - What the entry does depends on how the IRI ends:
        - **Ending in `#` or `/`** declares a namespace prefix. You can then write
          `your_prefix:your_suffix` in the Value and Ontology link columns of `@Schema`.
        - **Ending in anything else** names a single class of your own. Write the term on its own in
          the Value column, and it will be written as a `@type` that expands to your IRI.
    - This is how to ontologize something the BattINFO ontology does not cover yet, without adding
      it as a plain comment.
    - We only validate terms against the namespaces we cache, so terms in a namespace of your own
      are passed through unchecked.
    """
)

st.subheader("3. Adding terms to `@Predicates`")

st.markdown(
    """
    - Relationships between terms are defined with subject → predicate → object.
    - Predicates usually start with `has`, e.g. `hasProperty`, `hasCoating` etc.
    - The `@Predicates` tab allows us to assign a default `@type` to the object.
    - Both the type (`X`) and the predicate (`hasX`) must be ontology terms.
    - e.g. `hasBinder` has a default `@type` of `Binder`. Every time `hasBinder` is used, the object will have
      `{"@type": "Binder"}`.
    - Both `Binder` and `hasBinder` exist in the default context.
    - `hasMeasuredProperty`: has no default type, but it can be defined in the ontology link with e.g. `type|Thickness`.
    """
)

st.subheader("4. Adding classes to `@Classes`")

st.markdown(
    """
    - The `@Classes` tab lists classes that are useful in the Value column of `@Schema`, grouped by
      what part of the cell they belong to.
    - It is a convenience list, not a restriction. A class the ontology already knows works whether
      or not it is listed, so you only need to add a row to make a class easier for your users to
      find.
    - If a term is new in the [EMMO domain battery context](https://w3id.org/emmo/domain/battery/context)
      it may not yet be known to the app, in which case you do need to include it in `@Classes`. The
      term will then be converted correctly, despite the validator warning that the term is unknown.
    - Every class listed must exist in the ontology. To use something the ontology does not cover,
      declare it in `@Context` instead.
    """
)

st.subheader("5. Adding people and organisations to `@Individuals`")

st.markdown(
    """
    - `@Classes` is for kinds of things, e.g. a spacer has a type "Aluminium" - it is **an** aluminium thing,
      and there are other aluminium things that exist.
    - `@Individuals` is for specific individuals, usually people and organisations. e.g. the creator is **the**
      Corsin Battaglia, there is only one Corsin Battaglia in existance.
    - Each row has a 'Name' as written in `@Schema`, the 'Class' it belongs to, and an 'IRI' that
      identifies it.
    - Use an [ORCID](https://orcid.org) for a person and a [Wikidata](https://www.wikidata.org)
      entity for an organisation, in the form `http://www.wikidata.org/entity/Q683116`.
    - A row with no IRI still works: the name and class are recorded, and only the identifier is
      missing.
    """
)

st.subheader("6. Adding units to `@Units`")

st.markdown(
    """
    - In the `@Units` tab, add the symbol your users will type in the 'Unit' column, and the ontology
      class it means in the 'Unit class' column.
    - The class may be a term from the default namespace such as `MilliMetre`, a prefixed term such
      as `unit:MilliA-HR`, or a full IRI. It must resolve to an IRI, or the unit will not be
      ontologized.
    - The symbol can then be used in the 'Unit' column of the `@Schema` tab.
    - `unitless` is already provided for dimensionless measurements such as pH.
    """
)
