"""The ontology and taxonomy documents, checked against the spec and the build.

docs/taxonomy.md lists every coded value with a count, and docs/ontology.md maps each citation role
and vocabulary. Each claim is read out of the document and compared with schema/conformance.json,
and the counts with the built graph, so the documents cannot drift from what they describe.

The count checks skip where build/ has not been built.
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SPEC = json.loads((ROOT / "schema" / "conformance.json").read_text(encoding="utf-8"))
TAXONOMY = ROOT / "docs" / "taxonomy.md"
ONTOLOGY = ROOT / "docs" / "ontology.md"
GRAPH = ROOT / "build" / "dbms_research_kg.schema-candidate-v6.sqlite"
SCHEME_OF = {"Problem.problem_type": "problem-type",
             "Algorithm.family|System.family": "solution-technique-family",
             "ComputationModel.class": "computation-model-workload"}


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def value_tables(doc: str) -> dict[str, dict[str, int]]:
    """`### Label.property` -> {value: count} from the first `| Value | Count |` table under it."""
    out = {}
    for block in doc.split("\n### ")[1:]:
        heading = block.splitlines()[0].strip()
        rows = re.findall(r"^\| `([^`]+)` \| ([\d,]+) \|", block, re.MULTILINE)
        if rows:
            out[heading] = {v: int(n.replace(",", "")) for v, n in rows}
    return out


def scheme_tables(doc: str) -> dict[str, dict[str, int]]:
    """scheme -> {code: count} from the `| Code | Records |` table after its `(scheme `x`, n terms)`."""
    out = {}
    for scheme in SCHEME_OF.values():
        after = doc.split(f"(scheme `{scheme}`", 1)[1]
        table = after.split("| Code | Records |", 1)[1].split("\n\n", 1)[0]
        out[scheme] = {v: int(n.replace(",", "")) for v, n in re.findall(r"^\| `([^`]+)` \| ([\d,]+) \|",
                                                                          table, re.MULTILINE)}
    return out


def test_every_code_list_is_documented_with_exactly_its_values():
    tables = value_tables(text(TAXONOMY))
    for code, values in {**SPEC["codes"], **SPEC["property_values"]}.items():
        if code in SCHEME_OF:
            continue
        assert code in tables, f"no table for {code} in taxonomy.md"
        assert list(tables[code]) == values, code


def test_every_scheme_is_documented_with_exactly_its_codes():
    schemes = scheme_tables(text(TAXONOMY))
    for code, scheme in SCHEME_OF.items():
        assert list(schemes[scheme]) == SPEC["codes"][code], scheme


def test_topic_table_lists_the_35_topics():
    rows = re.findall(r"^\| (\d\d) \| `(\d\d-[a-z0-9-]+)` \|", text(TAXONOMY), re.MULTILINE)
    assert [n for n, _ in rows] == [f"{i:02d}" for i in range(1, 36)]
    assert all(topic.startswith(n + "-") for n, topic in rows)


def test_cito_table_matches_the_spec():
    rows = dict(re.findall(r"^\| (\w+) \| `cito:(\w+)` \|", text(ONTOLOGY), re.MULTILINE))
    expected = {role: prop for role, prop in SPEC["cito_roles"].items() if role != "artifact"}
    assert rows == expected


def test_every_declared_vocabulary_is_in_the_alignment_table():
    doc = text(ONTOLOGY).split("## Alignment with other vocabularies", 1)[1]
    names = {"dbms-domain": "Project DBMS domain ontology"}
    for vocabulary in SPEC["ontology_alignments"]:
        assert f"\n| {names.get(vocabulary, vocabulary)} |" in doc, vocabulary


def test_a_wrong_value_list_is_caught():
    """The parser must see a missing value, or the tests above can only pass."""
    doc = "\n### Problem.status\n\n| Value | Count | Meaning |\n|---|---:|---|\n| `open` | 1 | x |\n"
    assert list(value_tables(doc)["Problem.status"]) != SPEC["codes"]["Problem.status"]


# ---- counts, against the build ---------------------------------------------------------------

@pytest.fixture(scope="module")
def graph():
    if not GRAPH.is_file():
        pytest.skip("the v6 graph is not built")
    conn = sqlite3.connect(f"file:{GRAPH}?mode=ro", uri=True)
    try:
        nodes = [(label, json.loads(p)) for label, p in conn.execute("SELECT label, properties_json FROM nodes")]
        edges = [(rel, json.loads(p)) for rel, p in conn.execute("SELECT rel_type, properties_json FROM edges")]
    finally:
        conn.close()
    return nodes, edges


def measured(graph, code: str) -> Counter:
    nodes, edges = graph
    counts = Counter()
    for one in code.split("|"):
        label, prop = one.split(".")
        rows = edges if label in SPEC["relationships"] else nodes
        counts.update(p.get(prop) for name, p in rows if name == label)
    return counts


def test_value_counts_match_the_build(graph):
    for code, rows in value_tables(text(TAXONOMY)).items():
        if code not in {**SPEC["codes"], **SPEC["property_values"]}:
            continue
        counts = measured(graph, code)
        assert rows == {v: counts.get(v, 0) for v in rows}, code


def test_scheme_counts_match_the_build(graph):
    schemes = scheme_tables(text(TAXONOMY))
    for code, scheme in SCHEME_OF.items():
        counts = measured(graph, code)
        assert schemes[scheme] == {v: counts.get(v, 0) for v in schemes[scheme]}, scheme
