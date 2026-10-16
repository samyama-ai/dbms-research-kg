import pytest
from samyama import SamyamaClient

from etl.citations import paper_identity, parse_citation, person_key
from etl.loader import (
    create_nodes,
    create_relationships,
    person_name_form,
    prepare,
    stable_id,
    validate_paper_resume_ids,
)
from etl.repair_future_directions import audit_nodes, expected_future_ids


def test_citation_metadata_and_source_provenance():
    parsed = parse_citation(
        "**[Foundational]** C. Beeri, R. Fagin. *Database Schemes.* JACM, 1983. "
        "— [DOI](https://doi.org/10.1145/1234)",
        page_unverified=True,
    )
    # The page flag alone does not make a reference unverified; its own text must say so.
    assert parsed["title"] == "Database Schemes."
    assert parsed["year"] == 1983
    assert parsed["doi"] == "10.1145/1234"
    assert parsed["venue_raw"] == "JACM"
    assert parsed["verification_status"] == "source_only"
    assert parse_citation("**[SOTA]** X. *T.* SIGMOD 2000 *(unverified)*")["verification_status"] == "unverified"
    assert parsed["source_verified"] is False
    assert parsed["parse_status"] == "parsed"
    assert parsed["role"] == "foundational"
    assert parsed["authors"] == ["C. Beeri", "R. Fagin"]
    assert parsed["authors_raw"] == "C. Beeri, R. Fagin"


def test_artifact_citations_get_source_specific_cito_mappings():
    catalog = {
        "topics": [{"id": "topic", "title": "Topic", "source_path": "topics/topic"}],
        "problems": [{
            "id": "p", "title": "P", "status": "open", "topic_id": "topic",
            "source_path": "topics/topic/p.md", "metadata": {}, "sections": {},
            "future_work_items": [],
            "reference_entries": [
                ("**[Artifact]** Demirbas et al. *ClockBound and bounded-error time for distributed databases.* "
                "(AWS TimeSync ecosystem), 2021. — [GitHub](https://github.com/aws/clock-bound)"),
                ("**[Artifact]** Negi, Marcus, Mao, Tatbul, Kraska, Alizadeh. "
                "*Cardinality Estimation Benchmark (CEB).* (artifact/workload), 2021. — "
                "[GitHub](https://github.com/learnedsystems/CEB)"),
                ("**[Artifact]** A. Author. *Unclassified Artifact.* 2022. "
                "[GitHub](https://example.org/artifact)"),
            ],
        }],
    }
    data = prepare(catalog)
    mapped = {edge["artifact_kind"]: edge for edge in data["CITES"]}
    assert mapped["software-service"]["role"] == "artifact"
    assert mapped["software-service"]["role_raw"] == "Artifact"
    assert mapped["software-service"]["cito_property"] == "cites"
    assert "generic cito:cites" in mapped["software-service"]["cito_mapping_note"]
    assert mapped["benchmark-workload"]["cito_property"] == "citesAsDataSource"
    assert mapped["benchmark-workload"]["role"] == "artifact"
    fallback = next(edge for edge in data["CITES"] if edge["artifact_kind"] == "unspecified")
    assert fallback["cito_property"] == "cites"
    assert fallback["role_status"] == "source-explicit"


def test_uncertain_citation_keeps_raw_text():
    parsed = parse_citation("A loose   mention (1984)")
    assert parsed["citation_text"] == "A loose   mention (1984)"
    assert parsed["parse_status"] == "uncertain"
    assert parsed["title"] == ""


def test_citation_extraction_keeps_source_identifiers_and_initials_form():
    arxiv = parse_citation(
        "A. Author. *Paper.* arXiv preprint, 2020. "
        "[arXiv](https://arxiv.org/abs/2001.01234)")
    dblp = parse_citation(
        "A. Author. *Other Paper.* SIGMOD, 2021. "
        "[DBLP](https://dblp.org/rec/conf/sigmod/Author21.html)")
    assert arxiv["arxiv_id"] == "2001.01234"
    assert dblp["dblp_key"] == "conf/sigmod/Author21"
    assert person_name_form("D. Maier") == "initials"
    assert person_name_form("Maier") == "surname"


def test_identity_normalization_and_citation_variant_deduplication():
    a = parse_citation("A. Author. *A Paper Title.* Venue, 2020.")
    b = parse_citation("A. Author. **A Paper Title** Venue, 2020.")
    assert paper_identity(a) == paper_identity(b)
    assert person_key("M.Y. Vardi") == person_key("Vardi, M.Y.")
    catalog = {
        "topics": [{"id": "topic", "title": "Topic", "source_path": "topics/topic"}],
        "problems": [{
            "id": "p", "title": "P", "status": "open", "topic_id": "topic",
            "source_path": "topics/topic/p.md", "metadata": {}, "sections": {},
            "future_work_items": [],
            "reference_entries": ["A. Author. *A Paper Title.* Venue, 2020.",
                                  "A. Author. **A Paper Title** Venue, 2020."],
        }],
    }
    data = prepare(catalog)
    assert len(data["Paper"]) == 1
    assert len(data["CITES"]) == 1


def test_prepare_maps_provenance_and_deduplicates_papers():
    catalog = {
        "topics": [{"id": "topic", "title": "Topic", "source_path": "topics/topic"}],
        "problems": [{
            "id": "problem", "title": "Problem", "status": "open", "topic_id": "topic",
            "source_path": "topics/topic/problem.md", "metadata": {"refs_unverified": False},
            "sections": {"upper_bound": "O(n)", "lower_bound": "Ω(n)"},
            "future_work_items": ["Find a tighter bound"],
            "reference_entries": ["A. Author. *Paper Title.* Venue, 2020."] * 2,
        }],
    }
    data = prepare(catalog)
    assert len(data["Paper"]) == 1
    assert data["Paper"][0]["source_path"] == "topics/topic/problem.md"
    assert data["Paper"][0]["parse_status"] == "parsed"
    assert len(data["Person"]) == 1
    assert len(data["Venue"]) == 1
    assert len(data["CITES"]) == 1
    expected_future = stable_id("future", "problem\n0\nFind a tighter bound")
    assert data["FutureDirection"][0]["id"] == expected_future
    assert {"Topic", "Problem", "Paper", "Person", "Venue", "Bound", "FutureDirection",
            "Algorithm", "System", "Concept", "ComputationModel"} <= data.keys()
    assert {"IN_TOPIC", "HAS_BOUND", "CLOSING_REQUIRES", "CITES", "AUTHORED_BY",
            "APPEARED_AT", "STATE_OF_ART", "RESTS_ON", "IN_MODEL"} <= data.keys()


def test_allowlisted_entity_extraction_requires_source_phrase_and_keeps_provenance():
    catalog = {
        "topics": [{"id": "topic", "title": "Topic", "source_path": "topics/topic"}],
        "problems": [{
            "id": "p", "title": "P", "status": "open", "topic_id": "topic",
            "source_path": "topics/topic/p.md", "metadata": {},
            "sections": {"mathematical_foundations": "The treewidth of the hypergraph is bounded.",
                         "state_of_the_art": "Umbra uses the Yannakakis algorithm.",
                         "upper_bound": "O(n) in the word-RAM model."},
            "future_work_items": [], "reference_entries": [],
        }],
    }
    data = prepare(catalog)
    assert {n["name"] for n in data["Concept"]} == {"treewidth", "hypergraph"}
    assert [n["name"] for n in data["System"]] == ["Umbra"]
    assert [n["name"] for n in data["Algorithm"]] == ["Yannakakis algorithm"]
    assert [n["name"] for n in data["ComputationModel"]] == ["word-RAM"]
    assert all(n["source_path"] == "topics/topic/p.md"
               for label in ("Concept", "System", "Algorithm", "ComputationModel")
               for n in data[label])
    assert len(data["RESTS_ON"]) == 2
    assert len(data["STATE_OF_ART"]) == 2
    assert len(data["IN_MODEL"]) == 1


def test_related_edges_require_two_shared_papers_and_retain_evidence():
    topic = {"id": "topic", "title": "Topic", "source_path": "topics/topic"}
    refs = ["A. Author. *Paper One.* Venue, 2020.",
            "B. Author. *Paper Two.* Venue, 2021."]
    problems = []
    for problem_id, citations in (("p1", refs), ("p2", refs), ("p3", refs[:1])):
        problems.append({"id": problem_id, "title": problem_id, "status": "open",
            "topic_id": "topic", "source_path": f"topics/topic/{problem_id}.md",
            "metadata": {}, "sections": {}, "future_work_items": [],
            "reference_entries": citations})
    data = prepare({"topics": [topic], "problems": problems})
    assert len(data["RELATED_TO"]) == 1
    edge = data["RELATED_TO"][0]
    assert edge["shared_papers"] == 2
    assert edge["shared_evidence_count"] == 2
    assert len(edge["source_urls"]) == 2


class RecordingClient:
    def __init__(self):
        self.queries = []

    def query(self, query):
        self.queries.append(query)


def test_retry_queries_use_merge_for_nodes_and_edges():
    client = RecordingClient()
    node = [{"id": "p1", "title": "Problem"}]
    edge = [{"id": "p1->t1", "problem_id": "p1", "target_id": "t1"}]
    create_nodes(client, "Problem", node, 1)
    create_relationships(client, "IN_TOPIC", edge, 1)
    create_nodes(client, "Problem", node, 1)
    create_relationships(client, "IN_TOPIC", edge, 1)
    assert len(client.queries) == 4
    assert all("MERGE" in query for query in client.queries)
    assert not any("CREATE (" in query for query in client.queries)


@pytest.mark.parametrize("rel,record,source,target", [
    ("IN_TOPIC", {"id":"1", "problem_id":"p", "target_id":"t"}, "Problem", "Topic"),
    ("HAS_BOUND", {"id":"1", "problem_id":"p", "target_id":"b"}, "Problem", "Bound"),
    ("CLOSING_REQUIRES", {"id":"1", "problem_id":"p", "target_id":"f"}, "Problem", "FutureDirection"),
    ("CITES", {"id":"1", "problem_id":"p", "target_id":"x"}, "Problem", "Paper"),
    ("AUTHORED_BY", {"id":"1", "paper_id":"x", "target_id":"a"}, "Paper", "Person"),
    ("APPEARED_AT", {"id":"1", "paper_id":"x", "target_id":"v"}, "Paper", "Venue"),
    ("STATE_OF_ART", {"id":"1", "problem_id":"p", "target_id":"a", "target_label":"Algorithm"}, "Problem", "Algorithm"),
    ("STATE_OF_ART", {"id":"1", "problem_id":"p", "target_id":"s", "target_label":"System"}, "Problem", "System"),
    ("RESTS_ON", {"id":"1", "problem_id":"p", "target_id":"c"}, "Problem", "Concept"),
    ("IN_MODEL", {"id":"1", "bound_id":"b", "target_id":"m"}, "Bound", "ComputationModel"),
])
def test_relationship_endpoint_types(rel, record, source, target):
    client = RecordingClient()
    create_relationships(client, rel, [record], 1)
    query = client.queries[0]
    # endpoints matched as literals with WHERE (the id index is used), edge MERGEd
    assert query.startswith(f"MATCH (v0:{source}), (v1:{target}) WHERE v0.id = ")
    assert f"MERGE (v0)-[:{rel} " in query and query.endswith("]->(v1)")


def test_resume_id_check_accepts_existing_legacy_paper_id_and_rejects_mismatch():
    citation = "A. Author. *A Paper Title.* Venue, 2020."
    paper_id = stable_id("paper", citation.casefold())

    class ReadClient:
        def __init__(self, rows):
            self.rows = rows

        def query_readonly(self, _query):
            return type("Result", (), {"records": self.rows})()

    planned = [{"id": paper_id, **parse_citation(citation)}]
    assert validate_paper_resume_ids(ReadClient([[paper_id, citation]]), planned) == 0
    with pytest.raises(RuntimeError, match="different citation identity"):
        validate_paper_resume_ids(ReadClient([[paper_id, "Other title"]]), planned)


def test_all_supported_edge_queries_execute_and_replay_in_memory():
    client = SamyamaClient.embedded()
    node_ids = {
        "Problem": "p", "Topic": "t", "Bound": "b", "FutureDirection": "f",
        "Paper": "x", "Person": "a", "Venue": "v", "Algorithm": "alg",
        "System": "sys", "Concept": "c", "ComputationModel": "m",
    }
    for label, node_id in node_ids.items():
        create_nodes(client, label, [{"id": node_id, "name": node_id}], 1)
    edges = {
        "IN_TOPIC": [{"id":"1", "problem_id":"p", "target_id":"t"}],
        "HAS_BOUND": [{"id":"2", "problem_id":"p", "target_id":"b", "direction":"upper"}],
        "CLOSING_REQUIRES": [{"id":"3", "problem_id":"p", "target_id":"f", "position":1}],
        "CITES": [{"id":"4", "problem_id":"p", "target_id":"x", "role":"sota"}],
        "AUTHORED_BY": [{"id":"5", "paper_id":"x", "target_id":"a", "position":1}],
        "APPEARED_AT": [{"id":"6", "paper_id":"x", "target_id":"v"}],
        "STATE_OF_ART": [
            {"id":"7", "problem_id":"p", "target_id":"alg", "target_label":"Algorithm", "kind":"theory"},
            {"id":"8", "problem_id":"p", "target_id":"sys", "target_label":"System", "kind":"systems"},
        ],
        "RESTS_ON": [{"id":"9", "problem_id":"p", "target_id":"c"}],
        "IN_MODEL": [{"id":"10", "bound_id":"b", "target_id":"m"}],
    }
    for _ in range(2):
        for rel_type, records in edges.items():
            create_relationships(client, rel_type, records, 20)
    assert client.status().nodes == len(node_ids)
    assert client.status().edges == 10


def test_future_direction_index_shift_retry_is_detected_and_replay_uses_canonical_id():
    catalog = {
        "source": {"actual_commit": "pinned"},
        "problems": [{"id": "p", "source_path": "p.md",
                      "future_work_items": ["same work"]}],
    }
    expected = expected_future_ids(catalog)
    source_item = expected[("p", "same work")]
    old_id, shifted_id = source_item["canonical_id"], source_item["shifted_id"]
    observed = [
        [old_id, "p", "same work", "p.md"],
        [shifted_id, "p", "same work", "p.md"],
    ]
    assert audit_nodes(observed, expected) == [shifted_id]

    load_catalog = {
        "topics": [],
        "problems": [{"id": "p", "title": "P", "status": "open", "topic_id": "t",
                      "source_path": "p.md", "metadata": {}, "sections": {},
                      "future_work_items": ["same work"], "reference_entries": []}],
    }
    canonical = prepare(load_catalog)["FutureDirection"][0]
    assert canonical["id"] == old_id
    client = SamyamaClient.embedded()
    create_nodes(client, "Problem", [{"id": "p", "title": "P"}], 10)
    create_nodes(client, "FutureDirection", [
        {"id": old_id, "problem_id": "p", "text": "same work", "source_path": "p.md"},
        {"id": shifted_id, "problem_id": "p", "text": "same work", "source_path": "p.md"},
    ], 10)
    for _ in range(2):
        create_nodes(client, "FutureDirection", [canonical], 10)
        create_relationships(client, "CLOSING_REQUIRES", [{
            "id": f"p->{old_id}", "problem_id": "p", "target_id": old_id, "position": 1,
        }], 10)
    assert client.status().nodes == 3  # duplicate remains pending repair; no third ID appears
    assert client.status().edges == 1  # retry reuses the same canonical relationship
