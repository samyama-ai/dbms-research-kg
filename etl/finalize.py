"""Graph-wide steps after per-page extraction: hierarchy, related problems, taxonomy, provenance."""
from __future__ import annotations

import collections
import itertools
import json
from pathlib import Path

from etl.records import (
    PINNED_COMMIT,
    annotate_provenance,
    classification_evidence,
    stable_id,
)
from etl.source_entities import (
    CONCEPT_HIERARCHY,
    TOPIC_TECHNIQUE_FAMILY,
)


def finalize(data: dict, source: dict) -> dict:
    """Add GENERALIZES, RELATED_TO, taxonomy terms and classifications, page counts and provenance."""
    # GENERALIZES: the documented concept hierarchy, for concepts present in the graph.
    concept_ids = {c["name"]: c["id"] for c in data["Concept"]}
    for broader, narrower, rationale in CONCEPT_HIERARCHY:
        if broader in concept_ids and narrower in concept_ids:
            data["GENERALIZES"].append({
                "id": f"{concept_ids[broader]}->{concept_ids[narrower]}",
                "source_node_id": concept_ids[broader], "target_id": concept_ids[narrower],
                "method": "curated-hierarchy", "rationale": rationale})

    # RELATED_TO is computed only from identifiable shared catalog evidence.
    # A pair needs at least two distinct shared papers/concepts, one of them a
    # paper, so neither one ubiquitous citation nor common concepts create an edge.
    evidence_by_problem = collections.defaultdict(set)
    for edge in data["CITES"]:
        evidence_by_problem[edge["problem_id"]].add(("paper", edge["target_id"]))
    for edge in data["RESTS_ON"]:
        evidence_by_problem[edge["problem_id"]].add(("concept", edge["target_id"]))
    evidence_to_problems = collections.defaultdict(set)
    for problem_id, evidence_items in evidence_by_problem.items():
        for evidence_item in evidence_items:
            evidence_to_problems[evidence_item].add(problem_id)
    shared_by_pair = collections.defaultdict(set)
    for evidence_item, problem_ids in evidence_to_problems.items():
        for left, right in itertools.combinations(sorted(problem_ids), 2):
            shared_by_pair[(left, right)].add(evidence_item)
    problem_by_id = {p["id"]: p for p in data["Problem"]}
    for (left, right), shared in sorted(shared_by_pair.items()):
        # Two shared items, at least one of them a cited paper: concepts alone are
        # too common ("sampling", "entropy") to relate two problems by themselves.
        if len(shared) < 2 or not any(kind == "paper" for kind, _ in shared):
            continue
        union = evidence_by_problem[left] | evidence_by_problem[right]
        shared_papers = sum(kind == "paper" for kind, _ in shared)
        shared_concepts = sum(kind == "concept" for kind, _ in shared)
        paths = sorted({problem_by_id[x]["source_path"] for x in (left, right)})
        urls = [f"https://github.com/samyama-ai/dbms_research/blob/{PINNED_COMMIT}/{path}"
                for path in paths]
        data["RELATED_TO"].append({
            "id": f"{left}->{right}", "problem_id": left, "target_id": right,
            "method": "shared-papers-concepts",
            "score": round(len(shared) / len(union), 6),
            "shared_evidence_count": len(shared),
            "shared_papers": shared_papers, "shared_concepts": shared_concepts,
            "source_commit": PINNED_COMMIT, "source_urls": urls,
        })

    spec_path = Path(__file__).resolve().parents[1] / "schema" / "conformance.json"
    code_lists = json.loads(spec_path.read_text(encoding="utf-8"))["codes"]
    taxonomy_terms = {}

    def add_term(scheme, code, label):
        key = (scheme, code)
        if key not in taxonomy_terms:
            term_id = stable_id("taxonomy", scheme + "\n" + code)
            taxonomy_terms[key] = {"id": term_id, "scheme": scheme, "code": code,
                "name": label, "notation": code,
                "provenance": "schema-vocabulary", "source": "project_schema",
                "method": "list-matched", "retrieved_at": source.get("retrieved_at", "unknown"),
                "source_date": source.get("source_date", "unknown"),
                "source_url": "docs/schema.md"}
        return taxonomy_terms[key]["id"]

    for topic in data["Topic"]:
        add_term("dbms-topic", topic["id"], topic["name"])
    for code in code_lists["Problem.problem_type"]:
        add_term("problem-type", code, code.replace("-", " "))
    for code in code_lists["Algorithm.family|System.family"]:
        add_term("solution-technique-family", code, code.replace("-", " "))
    for code in code_lists["ComputationModel.class"]:
        add_term("computation-model-workload", code, code.replace("-", " "))
    data["TaxonomyTerm"] = list(taxonomy_terms.values())

    def classify(source_id, source_label, scheme, code, evidence_status, evidence):
        target_id = add_term(scheme, code, code.replace("-", " "))
        data["CLASSIFIED_AS"].append({
            "id": f"{source_id}->{target_id}", "source_node_id": source_id,
            "source_label": source_label, "target_id": target_id,
            "evidence_status": evidence_status, "evidence": evidence,
        })

    for p in data["Problem"]:
        classify(p["id"], "Problem", "problem-type", p["problem_type"],
                 p["classification_evidence_status"],
                 p["topic_id"] if p["problem_type_method"] == "topic-crosswalk" else classification_evidence(p))
        classify(p["id"], "Problem", "dbms-topic", p["topic_id"],
                 "source-explicit", p["topic_id"])
    # Family: the name rule first; otherwise the topic of the pages that cite the
    # name as state of the art (majority, ties to the lowest topic number).
    topics_by_target = collections.defaultdict(collections.Counter)
    topic_of = {p["id"]: p["topic_id"][:2] for p in data["Problem"]}
    for edge in data["STATE_OF_ART"]:
        topics_by_target[edge["target_id"]][topic_of[edge["problem_id"]]] += 1
    for label in ("Algorithm", "System"):
        for node in data[label]:
            if node["family"] != "unclassified":
                node["family_method"], node["family_evidence"] = "name-rule", node["name"]
            elif topics_by_target.get(node["id"]):
                votes = topics_by_target[node["id"]]
                topic = min(votes, key=lambda t: (-votes[t], t))
                node["family"] = TOPIC_TECHNIQUE_FAMILY.get(topic, "unclassified")
                node["family_method"], node["family_evidence"] = "topic-crosswalk", f"topic {topic}"
            else:
                node["family_method"], node["family_evidence"] = "none", node["name"]
            classify(node["id"], label, "solution-technique-family", node["family"],
                     "rule-based" if node["family"] != "unclassified" else "unresolved",
                     node["family_evidence"])
    for node in data["ComputationModel"]:
        classify(node["id"], "ComputationModel", "computation-model-workload", node["class"],
                 "rule-based" if node["class"] != "unclassified" else "unresolved",
                 node["name"])
    pages_by_paper = {}
    for edge in data["CITES"]:
        pages_by_paper.setdefault(edge["target_id"], set()).add(edge["problem_id"])
    pages_by_entity = {label: {} for label in ("Paper", "Person", "Venue", "Concept", "Algorithm", "System",
                                               "ComputationModel", "Institution")}
    for edge in data["ACTIVE_ON"]:
        if edge["source_label"] == "Institution":
            pages_by_entity["Institution"].setdefault(edge["source_node_id"], set()).add(edge["problem_id"])
    for edge in data["CITES"]:
        pages_by_entity["Paper"].setdefault(edge["target_id"], set()).add(edge["problem_id"])
    for edge in data["AUTHORED_BY"]:
        pages_by_entity["Person"].setdefault(edge["target_id"], set()).update(pages_by_paper.get(edge["paper_id"], set()))
    for edge in data["APPEARED_AT"]:
        pages_by_entity["Venue"].setdefault(edge["target_id"], set()).update(pages_by_paper.get(edge["paper_id"], set()))
    for edge in data["RESTS_ON"]:
        pages_by_entity["Concept"].setdefault(edge["target_id"], set()).add(edge["problem_id"])
    for edge in data["STATE_OF_ART"]:
        pages_by_entity[edge["target_label"]].setdefault(edge["target_id"], set()).add(edge["problem_id"])
    bound_problem = {b["id"]: b["problem_id"] for b in data["Bound"]}
    for edge in data["IN_MODEL"]:
        if edge["bound_id"] in bound_problem:
            pages_by_entity["ComputationModel"].setdefault(edge["target_id"], set()).add(bound_problem[edge["bound_id"]])
    for label, pages in pages_by_entity.items():
        for node in data[label]:
            node["page_count"] = len(pages.get(node["id"], set())) or 1
    # Shared entities retain the first source page and count distinct source pages.
    for label, records in data.items():
        if label in {"IN_TOPIC", "HAS_BOUND", "CLOSING_REQUIRES", "CITES", "AUTHORED_BY",
                     "APPEARED_AT", "STATE_OF_ART", "RESTS_ON", "IN_MODEL", "HAS_GAP",
                     "HAS_RESEARCH", "ACTIVE_ON", "AFFILIATED_WITH", "GENERALIZES",
                     "RELATED_TO", "FROM_SOURCE", "CLASSIFIED_AS"}:
            continue
        method = "list-matched" if label in {"Topic", "Concept", "Algorithm", "System", "ComputationModel", "TaxonomyTerm", "Institution"} else "parsed"
        annotate_provenance(records, source=source, default_method=method)
    node_labels = set(json.loads(spec_path.read_text(encoding="utf-8"))["labels"])
    node_source_paths = {
        record["id"]: record.get("source_path")
        for label, records in data.items() if label in node_labels
        for record in records if isinstance(record, dict) and record.get("id")
    }
    for rel, edges in data.items():
        if rel in {"IN_TOPIC", "HAS_BOUND", "CLOSING_REQUIRES", "CITES", "AUTHORED_BY",
                   "APPEARED_AT", "STATE_OF_ART", "RESTS_ON", "IN_MODEL", "HAS_GAP",
                   "HAS_RESEARCH", "ACTIVE_ON", "AFFILIATED_WITH", "GENERALIZES",
                   "RELATED_TO", "FROM_SOURCE", "CLASSIFIED_AS"}:
            for edge in edges:
                if rel == "RELATED_TO":
                    urls = edge["source_urls"]
                    edge["source_url"] = urls[0]
                    edge["source"] = "dbms_research"
                else:
                    source_id = (edge.get("problem_id") or edge.get("paper_id")
                                 or edge.get("bound_id") or edge.get("source_node_id")
                                 or edge.get("person_id") or edge.get("institution_id"))
                    source_path = node_source_paths.get(source_id)
                    if source_path and not edge.get("source_url"):
                        edge["source_url"] = (
                            f"https://github.com/samyama-ai/dbms_research/blob/{PINNED_COMMIT}/{source_path}")
                    edge["source"] = "dbms_research"
                    edge.setdefault("method", "parsed")
                    edge["source_commit"] = PINNED_COMMIT
    return data
