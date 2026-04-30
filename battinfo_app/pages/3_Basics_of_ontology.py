import streamlit as st

markdown_content = """
To share scientific data unambiguously, we want every piece of metadata to have a precise, agreed-upon meaning - this is
what an ontology provides.
Each term in your JSON-LD metadata file should point to an 'Internationalized Resource Identifier' (IRI) -- a unique web
address that defines the term -- or be a raw value such as a date, a number, or certain strings like names and dates.

In ontology, the "context" is both a way for us to not have to write out every single IRI, and a way for users within a
domain to agree on definitions. Our default context is the
[EMMO domain-battery](https://w3id.org/emmo/domain/battery/context) context. This is a big map of terms, so that when we
write, e.g., 'Aluminium', it looks up this term in our context, and sees that it points to the IRI
"https://w3id.org/emmo/domain/chemical-substance#substance_8f7dd877_5ad0_48f1_bbec_84153d8215f4". This link defines the
term and adds useful context, like molecular formula, IUPAC name, pubChem and Wikipedia links, and ensures we all agree
on the correct, British spelling. If someone else made their own context with "Aluminum" or "Alwminiwm" pointing to the
same IRI, tools would still understand they refer to the same concept.

What if something is not in our default context? We can add other namespaces. For example, we also have
`"schema": "https://schema.org/"` in our context. If we write `schema:name` in our metadata, tools will
replace `schema:` with the link we provided, so this term expands to the valid IRI "https://schema.org/name".
There is nothing clever happening here, it is just a shorthand for a link.

Ultimately, there are 4 ways a term gets put into the JSON-LD:

1. It is a term in the default context, e.g. "Aluminium", which maps to an IRI
2. It is a term that gets expanded, e.g. "schema:name", which expands to an IRI
3. It is already an IRI
4. It is a literal value, like a date "2026-04-30", a number "3.14", or a string literal like someone's name

"""
#####################################################################
st.title("Basics of ontology")
st.markdown(markdown_content, unsafe_allow_html=True)
