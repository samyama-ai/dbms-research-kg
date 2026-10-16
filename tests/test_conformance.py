import pytest

from etl.conformance import (
    ConformanceError,
    load_spec,
    validate,
    validate_ontology,
    validate_sqlite_alignments,
)
from etl.loader import prepare


@pytest.fixture
def conforming_data():
    catalog = {
        "source": {"repository": "https://github.com/samyama-ai/dbms_research",
                   "actual_commit": "5fff7f74508a52ac238f3bb608b8c8c872489fec",
                   "retrieved_at": "2026-10-14", "source_date": "2026-09-09"},
        "topics": [{"id": "01-test", "title": "Test", "source_path": "topics/01-test"}],
        "problems": [{
            "id": "01-test/p", "title": "P", "status": "open", "topic_id": "01-test",
            "source_path": "topics/01-test/p.md",
            "metadata": {"first_added": "2026-01", "last_reviewed": "2026-02",
                         "last_substantive_update": "2026-02", "refs_unverified": False,
                         "provenance": "synthesized"},
            "sections": {"problem_statement": "Query processing problem",
                         "mathematical_foundations": "treewidth",
                         "state_of_the_art": "Yannakakis algorithm",
                         "upper_bound": "O(n) time bound in the word-RAM model",
                         "lower_bound": "Ω(n) time bound", "gap": "**Open** Need a proof.",
                         "current_research": "- Develop a tighter algorithm", "future_work": "- Improve it",
                         "worked_example": "Example", "key_references": ""},
            "future_work_items": ["Improve it"], "reference_entries": [
                "**[Foundational]** A. Author. *A Paper.* JACM, 2020."
            ],
        }],
    }
    return prepare(catalog)


def test_prepared_source_graph_passes_machine_readable_conformance(conforming_data):
    assert validate(conforming_data) == []


def test_cito_artifact_mapping_is_validated_against_cited_paper(conforming_data):
    edge = conforming_data["CITES"][0]
    paper = next(node for node in conforming_data["Paper"] if node["id"] == edge["target_id"])
    paper["url"] = "https://github.com/learnedsystems/CEB"
    edge.update({"role": "artifact", "role_raw": "Artifact",
                 "artifact_kind": "benchmark-workload",
                 "cito_mapping_note": load_spec()["artifact_citation_mappings"][
                     "https://github.com/learnedsystems/CEB"]["note"],
                 "cito_property": "citesAsDataSource"})
    assert validate(conforming_data) == []
    # A valid value for some artifact records is wrong for this benchmark edge
    edge["cito_property"] = "cites"
    with pytest.raises(ConformanceError, match="CITES cito_property"):
        validate(conforming_data)


def test_cito_artifact_mapping_inventory_covers_both_meanings():
    spec = load_spec()
    mappings = spec["artifact_citation_mappings"]
    assert mappings["https://github.com/aws/clock-bound"]["cito_property"] == "cites"
    assert mappings["https://github.com/learnedsystems/CEB"]["cito_property"] == "citesAsDataSource"
    assert mappings["https://github.com/aws/clock-bound"]["artifact_kind"] == "software-service"
    assert mappings["https://github.com/learnedsystems/CEB"]["artifact_kind"] == "benchmark-workload"


def test_endpoint_and_controlled_value_errors_are_rejected(conforming_data):
    conforming_data["IN_TOPIC"][0]["target_id"] = "missing-topic"
    conforming_data["Problem"][0]["status"] = "unknown"
    with pytest.raises(ConformanceError) as exc:
        validate(conforming_data)
    assert "target endpoint" in str(exc.value)
    assert "outside controlled list" in str(exc.value)


def test_duplicate_identifiers_and_nonpinned_provenance_are_rejected(conforming_data):
    conforming_data["Topic"].append(dict(conforming_data["Topic"][0]))
    conforming_data["Problem"][0]["source"] = "external"
    errors = validate(conforming_data, raise_on_error=False)
    assert any("duplicate id" in e for e in errors)
    assert any("source crosses the pinned source boundary" in e for e in errors)


def test_all_declared_relationship_directions_match_schema():
    relationships = load_spec()["relationships"]
    assert relationships["AUTHORED_BY"] == ["Paper", "Person"]
    assert relationships["APPEARED_AT"] == ["Paper", "Venue"]
    assert relationships["CITES"] == ["Problem", "Paper"]
    assert len(relationships) == 17


def test_every_code_list_has_nonempty_unique_values():
    for name, values in load_spec()["codes"].items():
        assert values, name
        assert len(values) == len(set(values)), name


def test_required_node_and_relationship_properties_are_validated(conforming_data):
    conforming_data["Person"][0].pop("name_form")
    assert any("missing required property name_form" in error
               for error in validate(conforming_data, raise_on_error=False))


def test_uncertain_paper_keeps_raw_citation_without_inventing_a_title(conforming_data):
    paper = conforming_data["Paper"][0]
    paper["title"] = ""
    paper["parse_status"] = "uncertain"
    assert paper["citation_text"]
    assert validate(conforming_data) == []


def test_citation_edge_requires_position_and_pinned_provenance(conforming_data):
    conforming_data["CITES"][0].pop("position")
    errors = validate(conforming_data, raise_on_error=False)
    assert any("missing required relationship property position" in error for error in errors)


def test_ontology_parser_checks_inventory_mappings_and_datatype_properties():
    pytest.importorskip("rdflib")
    result = validate_ontology()
    assert result["status"] == "PASS", result["errors"]
    assert result["triple_count"] > 100


def test_ontology_parser_rejects_missing_vocabulary_mapping(tmp_path):
    pytest.importorskip("rdflib")
    from etl.conformance import ONTOLOGY_PATH

    text = ONTOLOGY_PATH.read_text(encoding="utf-8")
    broken = tmp_path / "broken.ttl"
    broken.write_text(text.replace(
        "kg:Topic a owl:Class ; rdfs:subClassOf skos:Concept ;",
        "kg:Topic a owl:Class ;",
        1,
    ), encoding="utf-8")
    result = validate_ontology(broken)
    assert result["status"] == "FAIL"
    assert any("kg:Topic rdfs:subClassOf skos:Concept" in error
               for error in result["errors"])


def test_ontology_parser_rejects_wrong_relationship_range(tmp_path):
    pytest.importorskip("rdflib")
    from etl.conformance import ONTOLOGY_PATH

    text = ONTOLOGY_PATH.read_text(encoding="utf-8")
    broken = tmp_path / "wrong-range.ttl"
    broken.write_text(text.replace(
        "kg:CITES a owl:ObjectProperty ; rdfs:domain kg:Problem ; rdfs:range kg:Paper ;",
        "kg:CITES a owl:ObjectProperty ; rdfs:domain kg:Problem ; rdfs:range kg:Person ;",
        1,
    ), encoding="utf-8")
    result = validate_ontology(broken)
    assert result["status"] == "FAIL"
    assert any("wrong RDF range for CITES" in error for error in result["errors"])


def test_existing_snapshot_is_not_misreported_as_v1_conformant():
    from pathlib import Path

    graph = Path(__file__).resolve().parents[1] / "build" / "dbms_research_kg.sqlite"
    if not graph.is_file():
        pytest.skip("repository SQLite graph artifact is not present")
    result = validate_sqlite_alignments(graph)
    assert result["node_count"] == 20019
    assert result["edge_count"] == 40189
    assert result["alignments"]["project_dbms_domain_ontology"]["status"] == "FAIL"
    assert result["alignments"]["PROV-O"]["status"] == "PARTIAL"


def test_existing_catalog_candidate_reports_each_alignment_separately():
    from pathlib import Path

    graph = Path(__file__).resolve().parents[1] / "build" / "dbms_research_kg.schema-candidate-v2.sqlite"
    if not graph.is_file():
        pytest.skip("repository catalog candidate is not present")
    result = validate_sqlite_alignments(graph)
    assert result["node_count"] == 19676
    assert result["edge_count"] == 41916
    # v2 predates the explicit per-edge CiTO mapping property added in v4.
    assert result["required_property_errors"] == 6157
    assert result["endpoint_errors"] == 0
    assert result["alignments"]["project_dbms_domain_ontology"]["status"] == "PARTIAL"
    assert result["alignments"]["PROV-O"]["status"] == "PASS"
    # Schema 1.1.0 added code values (Bound.kind approximation, eight ComputationModel
    # classes, Venue.kind book/report) whose taxonomy terms v2 predates.
    assert result["alignments"]["SKOS"]["status"] == "PARTIAL"
    assert result["alignments"]["CiTO"]["status"] == "PARTIAL"
    assert result["alignments"]["CiTO"]["evidence"]["edges_with_invalid_cito_mapping"] == 6159


def test_v6_candidate_passes_every_alignment_and_populates_every_type():
    from pathlib import Path

    graph = Path(__file__).resolve().parents[1] / "build" / "dbms_research_kg.schema-candidate-v6.sqlite"
    if not graph.is_file():
        pytest.skip("repository v6 catalog candidate is not present")
    result = validate_sqlite_alignments(graph)
    assert {name: a["status"] for name, a in result["alignments"].items()} == {
        name: "PASS" for name in result["alignments"]}
    spec = load_spec()
    assert set(result["node_counts"]) == set(spec["labels"])
    assert set(result["edge_counts"]) == set(spec["relationships"])
    assert result["required_property_errors"] == 0
