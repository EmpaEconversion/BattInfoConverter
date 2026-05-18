import streamlit as st
import json

st.title("Frequently asked questions")

st.markdown("**Q:** Why does it say my term 'was not found in the default namespace'?")
st.markdown(
    "**A:** The 'default namespace' is "
    "[EMMO domain-battery](https://w3id.org/emmo/domain/battery/context). "
    "This warning means the term you wrote does not map to an IRI, so it is not ontologized."
)

st.divider()

st.markdown("**Q:** How do I know what terms I can use?")
st.markdown(
    "**A:** Check the links in the context. The default is "
    "[EMMO domain-battery](https://w3id.org/emmo/domain/battery/context), "
    "with additional prefixed namespaces:"
)
st.code(
    json.dumps(
        {
            "schema": "https://schema.org/",
            "emmo": "https://w3id.org/emmo#",
            "echem": "https://w3id.org/emmo/domain/electrochemistry#",
            "battery": "https://w3id.org/emmo/domain/battery#",
            "chemical": "https://w3id.org/emmo/domain/chemical-substance#",
            "unit": "https://qudt.org/vocab/unit/",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        },
        indent=4,
    )
)

st.divider()

st.markdown("**Q:** Why does it say 'x is not understood as an ontology term, adding it as a comment'?")
st.markdown(
    "**A:** The term you used is not in the `@Classes` tab, so it is added as a comment instead of "
    "an ontologized term. If it is an ontology term in the default namespace, add it to `@Classes`. "
    "To intentionally add a comment, put `rdfs:comment` at the end of the ontology link instead."
)

st.divider()

st.markdown(
    "**Q:** Why does it say 'This is a 'schema:manufacturer' -- we recommend adding a unique ID in the @Classes tab.'?"
)
st.markdown(
    "**A:** If you add a person or manufacturer to the @Classes tab, it is properly expanded to an "
    "object with an @type, schema:name, and @id."
)
st.divider()

st.markdown("**Q:** Why does it say 'The URL for 'x' is not a known namespace of BattINFO converter'?")
st.markdown(
    "**A:** Certain prefixed namespaces are cached and the app validates terms against them. "
    "The URL may be misspelled, e.g. 'schema': 'https://schema.org' would mean 'schema:name' → "
    "'https://schema.orgname', which is wrong. If you added a custom namespace, you can ignore the warning."
)

st.divider()

st.markdown("**Q:** What is the difference between BattINFO converter and CatINFO converter?")
st.markdown(
    "**A:** The logos. Originally these were two apps with different logic, now they are powered "
    "by the same generalized backend. It doesn't matter which you use."
)

st.divider()

st.markdown("**Q:** Does anyone actually use ontology?")
st.markdown(
    "**A:** Yes! Most structured knowledge on the internet uses them, like Wikidata and Google's knowledge graph."
)

st.divider()

st.markdown("**Q:** Where can I find out more about ontologies in battery research?")
st.markdown(
    "**A:** See our papers [10.1002/aenm.202102702](https://doi.org/10.1002/aenm.202102702), "
    "[10.1002/cssc.202500458](https://doi.org/10.1002/cssc.202500458), and "
    "[10.1002/batt.202500151](https://doi.org/10.1002/batt.202500151)."
)

st.divider()

st.markdown("**Q:** This is only for metadata. What about data?")
st.markdown(
    "**A:** For battery data we recommend using the "
    "[battery data format](https://github.com/battery-data-alliance/battery-data-format) "
    "where possible."
)

st.divider()

st.markdown("**Q:** Something has gone wrong and this FAQ didn't help!")
st.markdown(
    "**A:** Raise an issue on the [GitHub page](https://github.com/EmpaEconversion/BattInfoConverter) and we will help."
)
