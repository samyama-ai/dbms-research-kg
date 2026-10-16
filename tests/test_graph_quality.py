"""Tests for the extraction and classification rules added for graph quality."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from etl.classify import bound_kind, gap_verdict, problem_type, technique_family
from etl.research_links import affiliation_mentions, resolve_affiliations
from etl.sota_entities import NameOracle, decide_labels, name_key, sota_mentions
from etl.source_entities import (
    CONCEPT_HIERARCHY,
    CONCEPTS,
    matching_concepts,
    matching_institutions,
    matching_models,
    model_class_code,
    venue_kind_code,
)

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "build" / "source_catalog.json"

SOTA = """- **Theory-SOTA:** **Yannakakis (1981)** gives linear time; **Chandra–Merlin** showed hardness.
  **PANDA** and **Free Join** are the frontier; **Adaptive** methods are **open**.
- **Systems-SOTA:** **DuckDB**, **Calvin/SLOG** and **Spanner** run it; **Ullman** wrote about it.
  **TPR-tree** indexes it; see **SQL** and **$O(n)$**."""

CORPUS = [SOTA, "adaptive adaptive adaptive methods are adaptive.", "We use Calvin and Spanner here."]


def oracle():
    return NameOracle(CORPUS)


# --- §3 names ---------------------------------------------------------------------

def test_bold_names_skip_labels_citations_authors_maths_and_common_words():
    found = [name for name, _ in sota_mentions(SOTA, oracle(), reject=set(),
                                              surnames=frozenset({"ullman"}))]
    assert found == ["PANDA", "Free Join", "DuckDB", "Calvin", "SLOG", "Spanner", "TPR-tree"]


def test_bullet_label_sets_the_context():
    mentions = dict(sota_mentions(SOTA, oracle(), reject=set()))
    assert mentions["PANDA"] == "theory"
    assert mentions["DuckDB"] == "systems"


def test_keep_list_overrides_the_surname_rule():
    text = "- **Systems-SOTA:** **Bao** learns hints."
    assert sota_mentions(text, oracle(), reject=set(), surnames=frozenset({"bao"})) == []
    assert sota_mentions(text, oracle(), reject=set(), surnames=frozenset({"bao"}),
                         keep=frozenset({"bao"})) == [("Bao", "systems")]


def test_labels_follow_majority_context_with_structure_names_as_algorithms():
    pages = [[("Calvin", "systems")], [("Calvin", "theory")], [("Calvin", "systems")],
             [("TPR-tree", "systems")], [("PANDA", "theory")]]
    labels = decide_labels(pages, systems_allowlist=())
    assert labels == {"calvin": "System", "tpr-tree": "Algorithm", "panda": "Algorithm"}


@pytest.mark.parametrize("bold", ["2EXPTIME", "NEXPTIME-complete", "coNP-hard", "Reuter's", "PSPACE"])
def test_complexity_classes_and_possessives_are_not_names(bold):
    assert sota_mentions(f"- **Theory:** **{bold}** here.", oracle(), reject=set()) == []


def test_name_key_unifies_dashes_and_case():
    assert name_key("Wander–Join") == name_key("wander-join")


# --- §7 institutions and affiliations ---------------------------------------------

def test_institutions_are_matched_from_the_checked_list_only():
    keys = [key for key, _, _ in matching_institutions("work from CMU, TUM and the UW–Madison group; Pavlo")]
    assert keys == ["cmu", "wisconsin", "tum"]


def test_affiliations_in_both_bracket_shapes():
    item = "Groups: Suciu (UW), Stoica/Yang (Berkeley), TUM (Neumann, Leis)."
    pairs = {(s, k) for s, k, _ in affiliation_mentions(item)}
    assert pairs == {("Suciu", "uw"), ("Stoica", "berkeley"), ("Yang", "berkeley"),
                     ("Neumann", "tum"), ("Leis", "tum")}


def test_affiliation_needs_exactly_one_cited_author_with_the_surname():
    page_authors = {"suciu": [("dan suciu", "Dan Suciu")],
                    "yang": [("a yang", "A. Yang"), ("b yang", "B. Yang")]}
    resolved = resolve_affiliations("Suciu (UW) and Yang (Berkeley)", page_authors)
    assert [(name, inst) for _, name, inst, _ in resolved] == [("Dan Suciu", "uw")]


# --- concepts, models, venues ------------------------------------------------------

def test_acronym_concepts_are_case_sensitive():
    assert "write-ahead logging" in matching_concepts("Recovery uses a WAL.")
    assert "write-ahead logging" not in matching_concepts("a wal of text")


def test_hierarchy_uses_known_concepts_and_has_no_cycles():
    names = set(CONCEPTS)
    edges = {(a, b) for a, b, _ in CONCEPT_HIERARCHY}
    assert all(a in names and b in names for a, b in edges)
    children = {}
    for a, b in edges:
        children.setdefault(a, set()).add(b)

    def reaches(start, goal, seen=()):
        return any(c == goal or (c not in seen and reaches(c, goal, (*seen, c)))
                   for c in children.get(start, ()))
    assert not any(reaches(a, a) for a in names)


def test_models_cover_conditional_hardness():
    found = matching_models("Under SETH no $O(n^{2-\\epsilon})$ algorithm exists; the problem is NP-hard.")
    assert {"SETH / fine-grained", "NP / classical"} <= set(found)
    assert model_class_code("SETH / fine-grained") == "fine-grained"


@pytest.mark.parametrize("venue,kind", [
    ("SIGMOD", "conference"), ("PVLDB", "journal"), ("J. ACM", "journal"), ("arXiv", "preprint"),
    ("Addison-Wesley", "book"), ("MSR-TR", "report"), ("IEEE Big Data", "conference"),
])
def test_venue_kinds(venue, kind):
    assert venue_kind_code(venue) == kind


# --- code lists -----------------------------------------------------------------------

@pytest.mark.parametrize("text,direction,kind", [
    ("Recognition runs in $O(|H|)$ time.", "upper", "time"),
    ("Evaluating CQs is NP-hard (Chandra-Merlin).", "lower", "impossibility"),
    ("Any filter needs $n\\log(1/\\epsilon)$ bits of space.", "lower", "space"),
    ("A 2-approximation ratio is achievable.", "upper", "approximation"),
    ("Nothing is said here.", "upper", "unclassified"),
])
def test_bound_kind(text, direction, kind):
    assert bound_kind(text, direction) == kind


@pytest.mark.parametrize("text,verdict,method", [
    ("**Open.** Nothing matches.", "open", "stated"),
    ("For acyclic joins the gap is **closed**. The genuinely **open** frontier is cyclic joins.",
     "partially-solved", "keyword"),
    ("The upper and lower bounds match up to constants.", "closed", "keyword"),
    ("It works in practice but lacks provable guarantees.", "empirically-open", "keyword"),
    ("The question remains open.", "open", "keyword"),
    ("", "unstated", "none"),
])
def test_gap_verdict(text, verdict, method):
    assert gap_verdict(text) == (verdict, method)


def test_problem_type_falls_back_to_the_topic():
    assert problem_type("Join ordering", "Choose a plan.", "02-query-optimization") == (
        "query-optimization", "rule-based", "statement-rule")
    assert problem_type("Mystery", "Nothing matches.", "05-concurrency-control") == (
        "transaction-processing", "rule-based", "topic-crosswalk")


def test_family_rules_prefer_product_names_for_systems():
    assert technique_family("DuckDB", "System") == "analytical-dbms"
    assert technique_family("Leapfrog Triejoin", "Algorithm") == "join-processing"
    assert technique_family("Crystal", "Algorithm") == "unclassified"


# --- the prepared graph from the pinned catalog -----------------------------------------

@pytest.fixture(scope="module")
def graph():
    if not CATALOG.is_file():
        pytest.skip("build/source_catalog.json is not present")
    from etl.loader import prepare
    return prepare(json.loads(CATALOG.read_text(encoding="utf-8")))


def test_every_label_and_relationship_is_populated(graph):
    from etl.conformance import load_spec, validate
    spec = load_spec()
    assert all(graph[label] for label in spec["labels"])
    assert all(graph[rel] for rel in spec["relationships"])
    assert validate(graph, raise_on_error=False) == []


def test_named_entities_are_not_citations_or_lowercase(graph):
    import re
    for label in ("Algorithm", "System"):
        for node in graph[label]:
            if node["extraction"] != "bold_name_in_section_3":
                continue                      # reviewed allowlist entries may be lower case
            assert not re.search(r"\b(19|20)\d\d\b", node["name"]), node["name"]
            assert node["name"][0].isupper() or node["name"][0].isdigit(), node["name"]


def test_related_to_always_has_a_shared_paper(graph):
    assert graph["RELATED_TO"]
    assert all(edge["shared_papers"] >= 1 for edge in graph["RELATED_TO"])


def test_submodular_width_generalizes_with_a_rationale(graph):
    names = {c["id"]: c["name"] for c in graph["Concept"]}
    pairs = {(names[e["source_node_id"]], names[e["target_id"]]) for e in graph["GENERALIZES"]}
    assert ("submodular width", "fractional hypertree width") in pairs
    assert all(e["rationale"] and e["method"] == "curated-hierarchy" for e in graph["GENERALIZES"])


def test_institution_edges_cite_the_problem_page(graph):
    edges = [e for e in graph["ACTIVE_ON"] if e["source_label"] == "Institution"]
    assert edges
    for edge in edges[:200]:
        assert edge["source_url"].endswith(edge["problem_id"] + ".md")
