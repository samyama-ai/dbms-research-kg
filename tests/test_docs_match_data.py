"""The schema is written down in several places; this pins them together.

schema/conformance.json is the machine-checked schema. The README, the dataset card, the design
notes, the ontology and the engine index file each list the labels and edge types again, and quote
counts. Nothing connected these, which is how a document comes to describe a graph that no longer
exists.

The first half parses the documents and needs no data. The second half checks the COUNTS quoted in
the documents against the built graph, and skips when build/ has not been built.
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SPEC = json.loads((ROOT / "schema" / "conformance.json").read_text(encoding="utf-8"))
LABELS = SPEC["labels"]
RELATIONS = list(SPEC["relationships"])
GRAPH = ROOT / "build" / "dbms_research_kg.schema-candidate-v6.sqlite"
README = ROOT / "README.md"
CARD = ROOT / "DATASET_CARD.md"
SCHEMA_DOC = ROOT / "docs" / "schema.md"
ONTOLOGY = ROOT / "docs" / "ontology.md"
INDEXES = ROOT / "schema" / "dbms_research_kg.cypher"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def bold_list(path: Path, heading: str) -> list[str]:
    """The names after `**16 node labels** --` (or `—`), up to the next blank line."""
    match = re.search(rf"^\*\*\d+ {heading}\*\* (?:--|—) (.*?)(?:\n\n|\Z)", text(path), re.DOTALL | re.MULTILINE)
    assert match, f"no **n {heading}** list in {path.name}"
    return [name.strip() for name in match.group(1).replace("\n", " ").split(",")]


def number(value: str) -> int:
    return int(value.replace(",", ""))


@pytest.mark.parametrize("path", [README, CARD], ids=lambda p: p.name)
def test_label_and_edge_lists_match_the_spec_in_order(path):
    assert bold_list(path, "node labels") == LABELS
    assert bold_list(path, "edge types") == RELATIONS


@pytest.mark.parametrize("path", [README, CARD], ids=lambda p: p.name)
def test_list_headings_count_what_they_list(path):
    assert re.search(rf"^\*\*{len(LABELS)} node labels\*\*", text(path), re.MULTILINE)
    assert re.search(rf"^\*\*{len(RELATIONS)} edge types\*\*", text(path), re.MULTILINE)


def test_every_label_has_an_id_index():
    indexed = re.findall(r"^CREATE INDEX ON :(\w+)\(id\);", text(INDEXES), re.MULTILINE)
    assert indexed == LABELS


def test_design_notes_describe_every_label_and_edge():
    doc = text(SCHEMA_DOC)
    assert sorted(re.findall(r"^\| `(\w+)` \| [\d,]+ \|", doc, re.MULTILINE)) == sorted(LABELS)
    assert sorted(re.findall(r"^\| `([A-Z_]+)` \| ", doc, re.MULTILINE)) == sorted(RELATIONS)


def test_ontology_defines_every_class():
    defined = re.findall(r"^\| \*\*(\w+)\*\* \|", text(ONTOLOGY), re.MULTILINE)
    assert sorted(defined) == sorted(LABELS)


def test_ontology_relations_match_the_spec_endpoints():
    rows = re.findall(r"^\| ([A-Z_]+) \| ([\w, ]+) \| ([\w, ]+) \| [\d.*]+ \|", text(ONTOLOGY), re.MULTILINE)
    found = {rel: ("|".join(d.split(", ")), "|".join(r.split(", "))) for rel, d, r in rows}
    assert found == {rel: tuple(ends) for rel, ends in SPEC["relationships"].items()}


def test_a_failing_list_is_caught(tmp_path):
    """The parser must see a wrong list, or the tests above can only pass."""
    doc = tmp_path / "doc.md"
    doc.write_text("**2 node labels** -- Problem, Topic\n\n", encoding="utf-8")
    assert bold_list(doc, "node labels") != LABELS


# ---- counts, against the build ---------------------------------------------------------------

@pytest.fixture(scope="module")
def counts():
    if not GRAPH.is_file():
        pytest.skip("the v6 graph is not built")
    conn = sqlite3.connect(f"file:{GRAPH}?mode=ro", uri=True)
    try:
        labels = dict(conn.execute("SELECT label, count(*) FROM nodes GROUP BY label"))
        relations = dict(conn.execute("SELECT rel_type, count(*) FROM edges GROUP BY rel_type"))
    finally:
        conn.close()
    return labels, relations


@pytest.mark.parametrize("path", [README, CARD], ids=lambda p: p.name)
def test_headline_totals_match_the_build(path, counts):
    labels, relations = counts
    match = re.search(r"\*\*([\d,]+) nodes\. ([\d,]+) edges\.", text(path))
    assert match, f"no headline count in {path.name}"
    assert (number(match.group(1)), number(match.group(2))) == (sum(labels.values()), sum(relations.values()))


def test_dataset_card_label_counts_match_the_build(counts):
    labels, _ = counts
    rows = dict(re.findall(r"^\| (\w+) \| ([\d,]+) \|$", text(CARD), re.MULTILINE))
    assert {label: number(n) for label, n in rows.items()} == labels


def test_design_notes_counts_match_the_build(counts):
    labels, relations = counts
    doc = text(SCHEMA_DOC)
    nodes = {k: number(v) for k, v in re.findall(r"^\| `(\w+)` \| ([\d,]+) \|", doc, re.MULTILINE)}
    edges = {k: number(v) for k, v in re.findall(r"^\| `([A-Z_]+)` \| [^|]+ \| ([\d,]+) \|", doc, re.MULTILINE)}
    assert nodes == labels
    assert edges == relations


def test_readme_schema_table_matches_the_build(counts):
    labels, relations = counts
    found = {}
    for line in text(README).splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.startswith("|") else []
        for name, value in zip(cells[::2], cells[1::2], strict=False):
            value = value.removesuffix(" each")
            if not re.fullmatch(r"[\d,]+", value):
                continue
            for one in name.removesuffix(" (computed)").split(", "):
                found[one] = number(value)
    assert {k: v for k, v in found.items() if k in labels} == labels
    assert {k: v for k, v in found.items() if k in relations} == relations
