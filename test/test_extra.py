"""Tests for the @Extra sheet with test and publication information."""

import copy

import pytest
from conftest import CellFixtures, normalize_jsonld
from pyld import jsonld

from battinfoconverter_backend.json_convert import INCLUDE_FIELD, convert_excel_to_jsonld
from battinfoconverter_backend.templates.template_conversion import dict_to_workbook, workbook_to_dict
from battinfoconverter_backend.validate import validate_jsonld

TEST_TYPE_FOR_CELL = {
    "CoinCell": "BatteryTest",
    "RedoxFlowBattery": "BatteryTest",
    "ElectrolyticCell": "ElectrolysisTest",
}


def _set_extra(template: dict, key: str, values: list) -> dict:
    """Return a copy of the template with one @Extra row changed."""
    template = copy.deepcopy(template)
    for row in template["@Extra"]["data"]:
        if row["key"] == key:
            row["values"] = values
            return template
    msg = f"{key} not in @Extra"
    raise KeyError(msg)


def _extra_fields(template: dict) -> tuple[dict, list]:
    """Read the @Extra rows of a template the way the converter does."""
    fields: dict[str, list] = {}
    authors: list[tuple[str, list]] = []
    in_authors = False
    for row in template["@Extra"]["data"]:
        if row["key"] == "Authors":
            in_authors = True
        elif in_authors:
            authors.append((row["key"], row["values"]))
        else:
            fields[row["key"]] = row["values"]
    return fields, authors


def _class_ids(template: dict) -> dict:
    """Map the @Classes items to their IDs."""
    return {row["Item"]: row["ID"] for row in template["@Classes"]["data"]}


def test_extra_excluded_by_default(schema: CellFixtures) -> None:
    """With 'Include this information' set to No, the cell stays at the root."""
    output = convert_excel_to_jsonld(dict_to_workbook(schema.template))
    assert "hasTestObject" not in output
    assert "hasOutput" not in output


def test_extra_wraps_cell_in_test(schema: CellFixtures, caplog: pytest.LogCaptureFixture) -> None:
    """With 'Include this information' set to Yes, the cell becomes the test object."""
    template = _set_extra(schema.template, INCLUDE_FIELD, ["Yes"])
    output = convert_excel_to_jsonld(dict_to_workbook(template))
    unwrapped = convert_excel_to_jsonld(dict_to_workbook(schema.template))

    test_type = TEST_TYPE_FOR_CELL[unwrapped["@type"]]
    assert output["@type"] == test_type
    assert output["hasTestObject"]["@type"] == unwrapped["@type"]
    # The converter credits describe the document, the sheet comments describe the cell
    credits_ = unwrapped["rdfs:comment"][:3]
    assert output["rdfs:comment"] == credits_
    assert output["hasTestObject"]["rdfs:comment"] == unwrapped["rdfs:comment"][3:]
    assert all(c.startswith(("BattINFO Converter", "Using template", "Software credit")) for c in credits_)

    unwrapped.pop("@context")
    unwrapped["rdfs:comment"] = unwrapped["rdfs:comment"][3:]
    assert normalize_jsonld(output["hasTestObject"]) == normalize_jsonld(unwrapped)

    fields, authors = _extra_fields(template)
    ids = _class_ids(template)

    result = output["hasOutput"]
    assert result["@type"] == [f"{test_type}Result", "dcat:Dataset"]
    assert result["dcterms:title"] == fields["Title"][0]
    assert result["dcterms:description"] == fields["Description"][0]
    assert result["dcterms:license"] == fields["License"][0]
    assert result["dcterms:issued"] == fields["Date issued"][0]
    assert result["schema:datePublished"] == fields["Date published"][0]
    assert result["schema:citation"] == fields["Citation"][0]
    assert result["dcat:keyword"] == fields["Keywords"]
    assert result["dcat:accessURL"] == fields["Dataset URL"][0]
    assert result["dcat:endpointURL"] == fields["Dataset API URL"][0]

    # The publisher is a research organization, with its @id from @Classes
    publisher = fields["Publisher"][0]
    assert result["dcterms:publisher"] == {
        "@type": "schema:ResearchOrganization",
        "@id": ids[publisher],
        "schema:name": publisher,
    }

    creators = result["dcterms:creator"]
    assert [c["schema:name"] for c in creators] == [name for name, _ in authors]
    for node, (name, affiliations) in zip(creators, authors, strict=True):
        # An ORCID or other ID is picked up from @Classes, absent if the person is not listed
        assert node.get("@id") == ids.get(name)
        affiliation = node["schema:affiliation"]
        # A single affiliation is one node, several are a list
        assert isinstance(affiliation, dict) == (len(affiliations) == 1)
        nodes = [affiliation] if isinstance(affiliation, dict) else affiliation
        for org, org_name in zip(nodes, affiliations, strict=True):
            assert org["@type"] == "schema:ResearchOrganization"
            assert org.get("@id") == ids.get(org_name)
            assert org["schema:name"] == org_name

    figures = result["schema:associatedMedia"]
    assert figures["@id"] == fields["Publication DOI"][0]
    assert figures["rdfs:label"] == fields["Figures"]
    assert figures["rdfs:comment"].startswith("Subfigure of associated")

    warnings = [w for w in caplog.text.splitlines() if "This is a 'schema:manufacturer' - " not in w]
    assert not [w for w in warnings if "recommended values" not in w]


def test_extra_expands_to_dublin_core(coincell: CellFixtures) -> None:
    """The dc and dcterms prefixes must expand to the Dublin Core IRIs."""
    template = _set_extra(coincell.template, INCLUDE_FIELD, ["Yes"])
    output = convert_excel_to_jsonld(dict_to_workbook(template), validate=False)
    expanded = jsonld.expand(output)

    def collect_keys(obj: dict | list, found: set) -> set:
        if isinstance(obj, dict):
            found.update(obj)
            for v in obj.values():
                collect_keys(v, found)
        elif isinstance(obj, list):
            for el in obj:
                collect_keys(el, found)
        return found

    keys = collect_keys(expanded, set())
    assert "http://purl.org/dc/terms/creator" in keys
    assert "http://purl.org/dc/terms/publisher" in keys
    assert "http://www.w3.org/ns/dcat#keyword" in keys
    assert not [k for k in keys if k.startswith(("dc:", "dcterms:"))]


@pytest.mark.parametrize(
    ("cell_type", "test_type"),
    [
        ("CoinCell", "BatteryTest"),
        ("RedoxFlowBattery", "BatteryTest"),
        ("ElectrolyticCell", "ElectrolysisTest"),
        ("PhotoelectrolyticCell", "ElectrolysisTest"),
        ("Electrolyser", "ElectrolysisTest"),
    ],
)
def test_test_type_follows_cell_type(coincell: CellFixtures, cell_type: str, test_type: str) -> None:
    """Electrolysis cells are tested by an ElectrolysisTest, anything else by a BatteryTest."""
    template = _set_extra(coincell.template, INCLUDE_FIELD, ["Yes"])
    rows = template["@Schema"]["data"]["Cell identification"]["rows"]
    next(r for r in rows if r["Metadata"] == "Cell type")["Value"] = cell_type

    output = convert_excel_to_jsonld(dict_to_workbook(template), validate=False)
    assert output["@type"] == test_type
    assert output["hasTestObject"]["@type"] == cell_type
    assert output["hasOutput"]["@type"] == [f"{test_type}Result", "dcat:Dataset"]


def test_extra_empty_template(schema: CellFixtures) -> None:
    """The empty template keeps the switches and drops example values and authors."""
    data = workbook_to_dict(dict_to_workbook(schema.template, empty=True))
    rows = {row["key"]: row["values"] for row in data["@Extra"]["data"]}
    assert rows[INCLUDE_FIELD] == ["No"]
    assert rows["Title"] == []
    assert rows["Keywords"] == []
    assert rows["Figures"] == []
    assert rows["Authors"] == ["Affiliations"]
    _, authors = _extra_fields(schema.template)
    assert not [name for name, _ in authors if name in rows]


def test_declared_prefix_accepted_unknown_rejected(coincell: CellFixtures, caplog: pytest.LogCaptureFixture) -> None:
    """Prefixes the remote context declares are accepted, others still warn."""
    template = _set_extra(coincell.template, INCLUDE_FIELD, ["Yes"])
    output = convert_excel_to_jsonld(dict_to_workbook(template), validate=False)
    output["hasOutput"]["bogus:publisher"] = "Empa"
    validate_jsonld(output, errors="warn")
    warnings = caplog.text.splitlines()
    assert [w for w in warnings if "bogus" in w]
    assert not [w for w in warnings if "dcterms" in w or "'dc'" in w]
