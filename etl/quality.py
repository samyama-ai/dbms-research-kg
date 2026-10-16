"""Quality criteria for a built catalog candidate, on top of the structural checks.

    python -m etl.quality --graph build/dbms_research_kg.schema-candidate-v5.sqlite \
        --report docs/quality-report.md

The structural checker (etl/conformance.py, etl/local_graph.py verify) proves the
graph has the declared shape. It passes a graph with no institutions or no
concept hierarchy. These criteria check the content: coverage, code-list
quality, entity hygiene and parity with the 2026-09 reference graph.
Exit status is 0 only when every criterion passes.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sqlite3
import sys
from pathlib import Path

from etl.conformance import load_spec, validate_sqlite_alignments
from etl.local_graph import inspect
from etl.source_entities import INSTITUTIONS

MIN_NODES, MIN_EDGES = 20_000, 40_000

# Measured on the 2026-09 reference snapshot (docs/phase1-log.md).
OLD_NODES = {"Problem": 1053, "Topic": 35, "Paper": 2962, "Person": 5193, "Venue": 480,
             "Institution": 1407, "Concept": 34, "Algorithm": 2808, "System": 108,
             "Bound": 2106, "ComputationModel": 8, "FutureDirection": 3825}
# Where this graph has fewer, the reason is a correction of the old graph.
JUSTIFIED_SHORTFALL = {
    "Paper": "citation identity (DOI, arXiv without version, DBLP key, title+year) merges records "
             "the old graph kept twice",
    "Institution": "only names on the checked list in etl/source_entities.py; the old graph's "
                   "1,407 included surnames (\"Pavlo\"), systems (\"Bao\") and topics",
    "Algorithm": "only names written in bold in §3; the old graph's 2,808 were mostly citations "
                 "such as \"Yannakakis (1981)\"",
}

# (property, values that count as "not classified", maximum share)
CODE_LIMITS = (
    ("Bound.kind", {"unclassified"}, 0.05),
    ("Gap.verdict", {"unstated"}, 0.10),
    ("Problem.problem_type", {"unclassified"}, 0.05),
    ("Venue.kind", {"other"}, 0.25),
    ("Algorithm.family", {"unclassified"}, 0.10),
    ("System.family", {"unclassified"}, 0.10),
    ("ComputationModel.class", {"unclassified"}, 0.0),
    ("Institution.kind", set(), 0.0),
    ("CITES.role", {"unclassified"}, 0.02),
    ("CLASSIFIED_AS.evidence_status", {"unresolved"}, 0.10),
)


def _rows(conn, table, kind_col, kind):
    return [json.loads(p) for (p,) in conn.execute(
        f"SELECT properties_json FROM {table} WHERE {kind_col}=?", (kind,))]


def evaluate(path: Path) -> list[dict]:
    """One dict per criterion: id, name, status (PASS/FAIL), measured, target, detail."""
    spec = load_spec()
    structural = inspect(path, verify=False)
    alignments = validate_sqlite_alignments(path)["alignments"]
    conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    try:
        nodes = dict(conn.execute("SELECT label,count(*) FROM nodes GROUP BY label"))
        edges = dict(conn.execute("SELECT rel_type,count(*) FROM edges GROUP BY rel_type"))
        results = []

        def add(cid, name, ok, measured, target, detail=""):
            results.append({"id": cid, "name": name, "status": "PASS" if ok else "FAIL",
                            "measured": measured, "target": target, "detail": detail})

        errors = (structural["duplicate_logical_nodes"] + structural["duplicate_logical_relationships"]
                  + structural["foreign_key_errors"] + structural["endpoint_type_errors"]
                  + structural["provenance_errors"] + structural["schema_data_errors"])
        add("Q1", "Structural conformance (schema, ids, endpoints, provenance)",
            errors == 0 and structural["sqlite_integrity_check"] == "ok", f"{errors} errors", "0 errors")
        passed = sum(a["status"] == "PASS" for a in alignments.values())
        add("Q2", "Ontology alignments", passed == len(alignments), f"{passed}/{len(alignments)} PASS",
            "all PASS", ", ".join(f"{k} {v['status']}" for k, v in alignments.items()))
        empty_labels = [label for label in spec["labels"] if not nodes.get(label)]
        empty_rels = [rel for rel in spec["relationships"] if not edges.get(rel)]
        add("Q3", "Every node label and relationship type populated", not empty_labels and not empty_rels,
            f"{len(spec['labels']) - len(empty_labels)}/{len(spec['labels'])} labels, "
            f"{len(spec['relationships']) - len(empty_rels)}/{len(spec['relationships'])} types",
            "all populated", "empty: " + ", ".join(empty_labels + empty_rels) if empty_labels or empty_rels else "")
        total_nodes, total_edges = sum(nodes.values()), sum(edges.values())
        add("Q4", "Graph size", total_nodes >= MIN_NODES and total_edges >= MIN_EDGES,
            f"{total_nodes:,} nodes, {total_edges:,} edges", f">= {MIN_NODES:,} nodes, >= {MIN_EDGES:,} edges")

        for i, (prop, bad, limit) in enumerate(CODE_LIMITS, 1):
            owner, key = prop.split(".")
            table, col = ("nodes", "label") if owner[0].isupper() and owner not in edges else ("edges", "rel_type")
            values = collections.Counter(r.get(key) for r in _rows(conn, table, col, owner))
            total = sum(values.values())
            share = sum(values[b] for b in bad) / total if total else 1.0
            add(f"Q5.{i}", f"Code list {prop}: unclassified share", total > 0 and share <= limit,
                f"{share:.1%} of {total:,}", f"<= {limit:.0%}",
                ", ".join(f"{k} {v}" for k, v in values.most_common()))

        concept_names = {r["id"]: r["name"] for r in _rows(conn, "nodes", "label", "Concept")}
        hierarchy = _rows(conn, "edges", "rel_type", "GENERALIZES")
        children = collections.defaultdict(set)
        for e in hierarchy:
            children[e["source_node_id"]].add(e["target_id"])

        def cyclic():
            state = {}

            def visit(n):
                state[n] = 1
                for c in children.get(n, ()):
                    if state.get(c) == 1 or (c not in state and visit(c)):
                        return True
                state[n] = 2
                return False
            return any(n not in state and visit(n) for n in list(children))
        add("Q6", "Concept hierarchy present, acyclic, every edge explained",
            bool(hierarchy) and not cyclic() and all(e.get("rationale") for e in hierarchy),
            f"{len(hierarchy)} GENERALIZES edges over {len(concept_names)} concepts", ">= 1, acyclic, rationale on each")
        topics_used = {r["topic_id"] for r in _rows(conn, "nodes", "label", "Problem")}
        topics = {r["id"] for r in _rows(conn, "nodes", "label", "Topic")}
        add("Q7", "Every topic has problems (flat 35-topic taxonomy)", topics == topics_used and len(topics) == 35,
            f"{len(topics_used)}/{len(topics)} topics used", "35/35")

        bad_names = []
        for label in ("Algorithm", "System"):
            for r in _rows(conn, "nodes", "label", label):
                if r.get("extraction") == "bold_name_in_section_3" and (
                        re.search(r"\b(?:19|20)\d\d\b|et al", r["name"]) or not (r["name"][0].isupper()
                                                                               or r["name"][0].isdigit())):
                    bad_names.append(r["name"])
        listed = {f"institution:{key}" for key, *_ in INSTITUTIONS}
        bad_inst = [r["name"] for r in _rows(conn, "nodes", "label", "Institution") if r["id"] not in listed]
        add("Q8", "Entity hygiene: no citation or lower-case names, institutions only from the checked list",
            not bad_names and not bad_inst, f"{len(bad_names)} bad names, {len(bad_inst)} unlisted institutions",
            "0 and 0", ", ".join((bad_names + bad_inst)[:10]))

        shortfalls = {label: (nodes.get(label, 0), old) for label, old in OLD_NODES.items()
                      if nodes.get(label, 0) < old}
        unexplained = [label for label in shortfalls if label not in JUSTIFIED_SHORTFALL]
        add("Q9", "Parity with the 2026-09 graph: every label reaches the old count or the shortfall is a fix",
            not unexplained, f"{len(OLD_NODES) - len(shortfalls)}/{len(OLD_NODES)} reach the old count, "
            f"{len(shortfalls) - len(unexplained)} justified", "no unexplained shortfall",
            "; ".join(f"{label} {new:,} vs {old:,}: {JUSTIFIED_SHORTFALL.get(label, 'UNEXPLAINED')}"
                      for label, (new, old) in shortfalls.items()))
        return results
    finally:
        conn.close()


def render(path: Path, results: list[dict]) -> str:
    passed = sum(r["status"] == "PASS" for r in results)
    lines = [
        "# Graph quality report", "",
        (f"Generated by `python -m etl.quality` for `{path.name}`. "
        f"**{passed} of {len(results)} criteria pass.**"), "",
        "| # | Criterion | Status | Measured | Target |", "|---|---|---|---|---|",
    ]
    lines += [f"| {r['id']} | {r['name']} | {r['status']} | {r['measured']} | {r['target']} |" for r in results]
    lines += ["", "## Details", ""]
    lines += [f"- **{r['id']}** {r['detail']}" for r in results if r["detail"]]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    results = evaluate(args.graph)
    for r in results:
        print(f"{r['status']:4}  {r['id']:6} {r['name']}: {r['measured']} (target {r['target']})")
    if args.report:
        args.report.write_text(render(args.graph, results), encoding="utf-8")
    return 0 if all(r["status"] == "PASS" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
