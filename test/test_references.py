"""Tests for the @References sheet with dataset and publication information."""

import copy
import json
from pathlib import Path
from urllib.parse import quote

import pytest
from conftest import CellFixtures, normalize_jsonld
from pyld import jsonld
from rdflib import Graph, URIRef

from battinfoconverter_backend.json_convert import INCLUDE_FIELD, convert_excel_to_jsonld
from battinfoconverter_backend.templates.template_conversion import dict_to_workbook, workbook_to_dict
from battinfoconverter_backend.validate import validate_jsonld

TEST_TYPE_FOR_CELL = {
    "CoinCell": "BatteryTest",
    "RedoxFlowBattery": "BatteryTest",
    "ElectrolyticCell": "ElectrolysisTest",
}


def _set_reference(template: dict, key: str, values: list) -> dict:
    """Return a copy of the template with one @References row changed, matched by its start."""
    template = copy.deepcopy(template)
    for row in template["@References"]["data"]:
        if str(row.get("key")).startswith(key):
            row["values"] = values
            return template
    msg = f"{key} not in @References"
    raise KeyError(msg)


def _switch(rows: dict) -> list:
    """Get the value of the include switch, whatever hint its label carries."""
    return next(v for label, v in rows.items() if label.startswith(INCLUDE_FIELD))


def _rows(template: dict) -> dict:
    """Map the @References labels to their values, skipping title rows."""
    return {row["key"]: row["values"] for row in template["@References"]["data"] if not row.get("type")}


def _authors(template: dict, prefix: str) -> list[tuple[str, list]]:
    """Get the (name, affiliations) of the suffixed author rows of one section."""
    rows = _rows(template)
    keys = sorted(k for k in rows if k.startswith(f"{prefix} author"))
    return [(rows[k][0], rows[k][1:]) for k in keys]


def _class_ids(template: dict) -> dict:
    """Map the @Classes items to their IDs."""
    ids = {}
    for row in template["@Classes"]["data"]:
        item = row.get("Item", row.get("Class"))
        ids[item] = row.get("ID", row.get("Class IRI"))
    return ids


def test_references_included_by_default(schema: CellFixtures) -> None:
    """The filled templates have the switch on, so the test is the root object."""
    output = convert_excel_to_jsonld(dict_to_workbook(schema.template))
    assert "hasTestObject" in output
    assert "hasOutput" in output


def test_references_excluded_when_switched_off(schema: CellFixtures) -> None:
    """With the switch set to no, the cell stays at the root."""
    template = _set_reference(schema.template, INCLUDE_FIELD, ["no"])
    output = convert_excel_to_jsonld(dict_to_workbook(template))
    assert "hasTestObject" not in output
    assert "hasOutput" not in output


def test_references_wrap_cell_in_test(schema: CellFixtures, caplog: pytest.LogCaptureFixture) -> None:
    """With the switch set to yes, the cell becomes the test object."""
    template = schema.template
    output = convert_excel_to_jsonld(dict_to_workbook(template))
    unwrapped = convert_excel_to_jsonld(dict_to_workbook(_set_reference(template, INCLUDE_FIELD, ["no"])))

    test_type = TEST_TYPE_FOR_CELL[unwrapped["@type"]]
    assert output["@type"] == test_type
    assert output["hasTestObject"]["@type"] == unwrapped["@type"]
    # The converter credits describe the document, the sheet comments describe the cell
    credits_ = unwrapped["rdfs:comment"][:3]
    assert output["rdfs:comment"] == credits_
    assert output["hasTestObject"]["rdfs:comment"] == unwrapped["rdfs:comment"][3:]

    unwrapped.pop("@context")
    unwrapped["rdfs:comment"] = unwrapped["rdfs:comment"][3:]
    assert normalize_jsonld(output["hasTestObject"]) == normalize_jsonld(unwrapped)

    rows = _rows(template)
    result = output["hasOutput"]
    assert result["@type"] == [f"{test_type}Result", "dcat:Dataset"]
    assert result["dcterms:title"] == rows["Dataset name"][0]
    assert result["dcterms:description"] == rows["Dataset description"][0]
    assert result["dcterms:license"] == {"@id": rows["Dataset license"][0]}
    assert result["dcterms:issued"] == rows["Dataset date issued"][0]
    assert result["schema:datePublished"] == rows["Dataset date published"][0]
    assert result["dcat:accessURL"] == {"@id": rows["Dataset URL"][0]}
    assert result["dcat:endpointURL"] == {"@id": rows["Dataset API URL"][0]}

    ids = _class_ids(template)
    publisher = rows["Dataset publisher"][0]
    assert result["dcterms:publisher"] == {
        "@type": "schema:ResearchOrganization",
        "@id": ids[publisher],
        "schema:name": publisher,
    }
    _assert_people(result["dcterms:creator"], _authors(template, "Dataset"), ids)

    publication = result["schema:associatedMedia"]
    assert publication["@id"] == rows["Associated publication DOI"][0]
    assert publication["dcterms:title"] == rows["Associated publication title"][0]
    assert publication["rdfs:label"] == rows["Associated publication figures"]
    assert publication["rdfs:comment"].startswith("Subfigure of associated")
    _assert_people(publication["dcterms:creator"], _authors(template, "Associated publication"), ids)

    warnings = [w for w in caplog.text.splitlines() if "This is a 'schema:manufacturer' - " not in w]
    assert not [w for w in warnings if "recommended values" not in w]


def _assert_people(nodes: list[dict], authors: list[tuple[str, list]], ids: dict) -> None:
    """The people of a section, in sheet order, with their affiliations."""
    assert [node["schema:name"] for node in nodes] == [name for name, _ in authors]
    for node, (name, affiliations) in zip(nodes, authors, strict=True):
        # An ORCID or other ID is picked up from @Classes, absent if the person is not listed
        assert node.get("@id") == ids.get(name)
        affiliation = node["schema:affiliation"]
        # A single affiliation is one node, several are a list
        assert isinstance(affiliation, dict) == (len(affiliations) == 1)
        orgs = [affiliation] if isinstance(affiliation, dict) else affiliation
        for org, org_name in zip(orgs, affiliations, strict=True):
            assert org["@type"] == "schema:ResearchOrganization"
            assert org.get("@id") == ids.get(org_name)
            assert org["schema:name"] == org_name


def test_references_expand_to_dublin_core(coincell: CellFixtures) -> None:
    """The dcterms and dcat prefixes must expand to their real IRIs."""
    template = coincell.template
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
    assert "http://www.w3.org/ns/dcat#accessURL" in keys
    assert not [k for k in keys if k.startswith(("dcterms:", "dcat:"))]


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
    template = coincell.template
    rows = template["@Schema"]["data"]["Cell identification"]["rows"]
    next(r for r in rows if r["Metadata"] == "Cell type")["Value"] = cell_type

    output = convert_excel_to_jsonld(dict_to_workbook(template), validate=False)
    assert output["@type"] == test_type
    assert output["hasTestObject"]["@type"] == cell_type
    assert output["hasOutput"]["@type"] == [f"{test_type}Result", "dcat:Dataset"]


def test_empty_template_switches_references_off(schema: CellFixtures) -> None:
    """The empty template keeps the layout, drops the values, and turns the switch off."""
    empty = dict_to_workbook(schema.template, empty=True)
    data = workbook_to_dict(empty)
    entries = data["@References"]["data"]
    filled = schema.template["@References"]["data"]

    # The title rows survive with their styling
    assert [e for e in entries if e.get("type")] == [e for e in filled if e.get("type")]

    rows = {e["key"]: e["values"] for e in entries if not e.get("type")}
    assert set(rows) == set(_rows(schema.template))
    assert _switch(rows) == ["no"]
    assert _switch(_rows(schema.template)) == ["yes"]  # the filled template has it on
    assert all(not values for label, values in rows.items() if not label.startswith(INCLUDE_FIELD))

    # An empty template converts to a bare cell, not a test
    assert "hasTestObject" not in convert_excel_to_jsonld(empty, validate=False)


def test_declared_prefix_accepted_unknown_rejected(coincell: CellFixtures, caplog: pytest.LogCaptureFixture) -> None:
    """Prefixes the remote context declares are accepted, others still warn."""
    template = coincell.template
    output = convert_excel_to_jsonld(dict_to_workbook(template), validate=False)
    output["hasOutput"]["bogus:publisher"] = "Empa"
    validate_jsonld(output, errors="warn")
    warnings = caplog.text.splitlines()
    assert [w for w in warnings if "bogus" in w]
    assert not [w for w in warnings if "dcterms" in w or "dcat" in w]


SCHEMAS = {
    "CoinCell": "https://w3id.org/battery-data-alliance/ontology/battery-data-format/schema",
    "RedoxFlowBattery": "https://w3id.org/battery-data-alliance/ontology/battery-data-format/schema",
    "ElectrolyticCell": "https://w3id.org/catalysis-data-format/schema",
}
IANA = "https://www.iana.org/assignments/media-types/"
MEDIA_TYPES = {
    ".parquet": "application/vnd.apache.parquet",
    ".csv": "text/csv",
    ".mpr": "application/octet-stream",
}


def test_data_files_become_distributions(schema: CellFixtures) -> None:
    """Each data file row becomes a dcat:Distribution of the dataset."""
    template = schema.template
    output = convert_excel_to_jsonld(dict_to_workbook(template), validate=False)
    rows = _rows(template)
    files = [rows[k] for k in sorted(rows) if k.startswith("Data file")]
    distributions = output["hasOutput"]["dcat:distribution"]

    assert len(distributions) == len(files)
    for node, (path, comment) in zip(distributions, files, strict=True):
        assert node["@id"] == path
        assert node["@type"] == "dcat:Distribution"
        assert node["dcat:mediaType"] == {"@id": IANA + MEDIA_TYPES[Path(path).suffix]}
        assert node["rdfs:comment"] == comment


def test_tabular_files_get_the_schema_of_the_cell(schema: CellFixtures) -> None:
    """Battery cells use the Battery Data Format, electrolysis cells the Catalysis one."""
    output = convert_excel_to_jsonld(dict_to_workbook(schema.template), validate=False)
    expected = SCHEMAS[output["hasTestObject"]["@type"]]
    for node in output["hasOutput"]["dcat:distribution"]:
        assert node["csvw:tableSchema"] == {"@id": expected}
        # only CSV needs its dialect spelled out
        assert ("csvw:dialect" in node) == node["@id"].endswith(".csv")


def test_raw_files_are_inputs(schema: CellFixtures) -> None:
    """Raw instrument files describe what went into the test, not what came out."""
    template = schema.template
    output = convert_excel_to_jsonld(dict_to_workbook(template), validate=False)
    rows = _rows(template)
    raw_paths = [rows[k][0] for k in sorted(rows) if k.startswith("Raw data file")]

    node = output["hasInput"]
    assert node["@type"] == ["RawData", "dcat:Dataset"]
    assert [d["@id"] for d in node["dcat:distribution"]] == raw_paths
    for distribution in node["dcat:distribution"]:
        assert distribution["@type"] == ["dcat:Distribution", "RawData"]
        # raw files are not tabular, so they carry no schema
        assert "csvw:tableSchema" not in distribution
    # and they are not repeated as outputs
    assert not set(raw_paths) & {d["@id"] for d in output["hasOutput"]["dcat:distribution"]}


def test_download_urls_point_into_the_zenodo_zip(schema: CellFixtures) -> None:
    """The file's @id stays a path in the dataset, the download URL resolves on Zenodo."""
    template = schema.template
    rows = _rows(template)
    record = rows["Dataset URL"][0].rsplit(".", 1)[-1]
    zip_name = rows["Data zip file"][0]
    output = convert_excel_to_jsonld(dict_to_workbook(template), validate=False)

    for node in output["hasOutput"]["dcat:distribution"]:
        expected = f"https://zenodo.org/records/{record}/files/{quote(zip_name)}#{node['@id']}"
        assert node["dcat:downloadURL"] == {"@id": expected}


def test_download_url_without_a_zip_is_a_direct_file(coincell: CellFixtures) -> None:
    """Without a zip the files are uploaded individually, so each gets a direct URL."""
    template = _set_reference(coincell.template, "Data zip file", [])
    output = convert_excel_to_jsonld(dict_to_workbook(template), validate=False)
    record = _rows(template)["Dataset URL"][0].rsplit(".", 1)[-1]
    node = output["hasOutput"]["dcat:distribution"][0]
    assert node["dcat:downloadURL"] == {"@id": f"https://zenodo.org/records/{record}/files/{node['@id']}"}


def test_files_without_a_dataset_url_keep_their_paths(coincell: CellFixtures) -> None:
    """Before the dataset is published there is no URL, but the files are still identified."""
    template = _set_reference(coincell.template, "Dataset URL", [])
    output = convert_excel_to_jsonld(dict_to_workbook(template), validate=False)
    for node in output["hasOutput"]["dcat:distribution"]:
        assert node["@id"]
        assert "dcat:downloadURL" not in node


def test_file_paths_validate_but_mistyped_terms_do_not(coincell: CellFixtures) -> None:
    """A file path in an @id is a relative reference, a bare word is a mistyped term."""
    output = convert_excel_to_jsonld(dict_to_workbook(coincell.template), validate=True)
    validate_jsonld(output, errors="raise")  # the file paths must not raise

    output["hasOutput"]["dcat:distribution"].append({"@id": "ThisDoesNotExist"})
    with pytest.raises(ValueError, match="'ThisDoesNotExist' was not found"):
        validate_jsonld(output, errors="raise")


def test_links_are_nodes_not_text(coincell: CellFixtures) -> None:
    """URLs must stay links when merged into a document with another context."""
    output = convert_excel_to_jsonld(dict_to_workbook(coincell.template), validate=False)
    result = output["hasOutput"]
    for key in ("dcterms:license", "dcat:accessURL", "dcat:endpointURL"):
        assert set(result[key]) == {"@id"}
    for key in ("dcat:downloadURL", "dcat:mediaType", "csvw:tableSchema"):
        assert set(result["dcat:distribution"][0][key]) == {"@id"}

    # Dropping the local context must not turn them into literals
    bare = {
        "@context": "https://w3id.org/emmo/domain/battery/context",
        **{k: v for k, v in output.items() if k != "@context"},
    }
    graph = Graph().parse(data=json.dumps(bare), format="json-ld")
    for predicate in (
        "http://purl.org/dc/terms/license",
        "http://www.w3.org/ns/dcat#accessURL",
        "http://www.w3.org/ns/dcat#downloadURL",
        "http://www.w3.org/ns/dcat#endpointURL",
        "http://www.w3.org/ns/dcat#mediaType",
        "http://www.w3.org/ns/csvw#tableSchema",
    ):
        objects = [o for _, p, o in graph if str(p) == predicate]
        assert objects, predicate
        assert all(isinstance(o, URIRef) for o in objects), predicate


def test_values_that_cannot_be_links_stay_text_and_warn(
    coincell: CellFixtures, caplog: pytest.LogCaptureFixture
) -> None:
    """A license or schema that is not a URL is kept as text, and the user is told once."""
    template = _set_reference(coincell.template, "Dataset license", ["CC BY 4.0"])
    template = _set_reference(template, "Tabular data schema", ["battery data format"])
    output = convert_excel_to_jsonld(dict_to_workbook(template), validate=False)

    assert output["hasOutput"]["dcterms:license"] == "CC BY 4.0"
    assert output["hasOutput"]["dcat:distribution"][0]["csvw:tableSchema"] == "battery data format"

    warnings = [w for w in caplog.text.splitlines() if "should be a URL" in w]
    assert len(warnings) == 2  # one per row, not one per file
    assert any("Dataset license" in w for w in warnings)
    assert any("Tabular data schema" in w for w in warnings)
