import streamlit as st

st.title("Basics of Ontology")

st.markdown(
    """
    To share scientific data unambiguously, we want every piece of metadata to have a precise, agreed-upon meaning; this
    is what an ontology provides.

    Each term in your JSON-LD metadata file should point to an **Internationalized Resource Identifier (IRI)** -- a
    unique web address that defines the term -- or be a raw value such as a date, a number, or certain strings like
    names and dates.
    """
)

st.subheader("Context")

st.markdown(
    """
    In ontology, the "context" is both a way for us to avoid writing out every single IRI, and a way for users within a
    domain to agree on definitions. Our default context is the
    [EMMO domain-battery](https://w3id.org/emmo/domain/battery/context) context.

    This is a large map of terms, so that when we write, e.g., `Aluminium`, it looks up this term in our context and
    resolves it to:
    """
)

st.code("https://w3id.org/emmo/domain/chemical-substance#substance_8f7dd877_5ad0_48f1_bbec_84153d8215f4", language=None)

st.markdown(
    """
    This link defines the term and adds useful context such as molecular formula, IUPAC name, PubChem and Wikipedia
    links, and ensures we all agree on the correct, British spelling. If someone else made their own context with
    `Aluminum` or `Alwminiwm` pointing to the same IRI, tools would still understand they refer to the same concept.
    """
)

st.subheader("Prefixed Namespaces")

st.markdown(
    """
    What if we want to use terms not in our default context, but still don't want to write out full IRIs? Then we use
    prefixed namespaces. For example, we have `"schema": "https://schema.org/"` in our context. This means that when we
    add the prefix `schema:`, tools will replace this with the link provided, so e.g. `schema:name` expands to the valid
    IRI `https://schema.org/name`.

    There is nothing clever happening here, it is just a shorthand for a link.
    """
)

st.subheader("How Terms Appear in JSON-LD")

st.markdown("Ultimately, there are 4 ways a value gets put into the JSON-LD:")

col1, col2 = st.columns([0.05, 0.95])
items = [
    "It is already **an IRI**",
    "It is in the **default context** which **maps to an IRI**, e.g. `Aluminium`",
    "It is in another namespace that **expands to an IRI**, e.g. `schema:name`",
    "It is a **literal value**, like a date `2026-04-30`, a number `3.14`, or a string like someone's name",
]

for num, text in enumerate(items):
    with st.container(border=True):
        c1, c2 = st.columns([0.06, 0.94])
        c1.markdown(f"**{num + 1})**")
        c2.markdown(text)
