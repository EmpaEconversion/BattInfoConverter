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

st.markdown("**Q:** Why does it say my value 'is recorded as a comment'?")
st.markdown(
    "**A:** The value is neither listed in the `@Classes` tab nor a term the context can expand, so "
    "it cannot be ontologized. The warning suggests close matches, which usually points at a "
    "misspelling. Otherwise: add it to `@Classes` if it is a class, declare it in `@Context` if it "
    "is your own, or write `comment|` in front of the value to record it as text on purpose."
)

st.divider()

st.markdown("**Q:** Why does it say my value 'has a numerical value x with no unit, which is ambiguous'?")
st.markdown(
    "**A:** A number in a cell that expects an ontology class is almost always a measurement whose "
    "Unit cell was left empty. Give the row a unit from the `@Units` tab. If the quantity really is "
    "dimensionless, such as pH, use `unitless`. If it is not a measurement at all, write `comment|` "
    "in front of it, or put it on a literal predicate such as `schema:productID`."
)

st.divider()

st.markdown('**Q:** Why does it say "we recommend listing it with an IRI in @Individuals"?')
st.markdown(
    "**A:** The person or organisation is converted, but without an identifier anyone else can "
    "resolve. Add a row to the `@Individuals` tab with the name, its class, and an IRI: an "
    "[ORCID](https://orcid.org) for a person, or a [Wikidata](https://www.wikidata.org) entity such "
    "as `http://www.wikidata.org/entity/Q683116` for an organisation."
)
st.divider()

st.markdown("**Q:** Why does it say 'The URL for 'x' is not a known namespace of BattINFO converter'?")
st.markdown(
    "**A:** Certain prefixed namespaces are cached and the app validates terms against them. "
    "The warning only appears when your URL is very close to one we know, so it almost always means "
    "a typo, e.g. 'schema': 'https://schema.org' would mean 'schema:name' → 'https://schema.orgname', "
    "which is wrong. A namespace of your own that looks nothing like ours is accepted silently, and "
    "its terms are simply not checked."
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
