"""Item-by-item audit of a built graph against docs/standards.md.

    python -m etl.audit --graph build/dbms_research_kg.schema-candidate-v5.sqlite \
        --part taxonomies|code-lists|all [--report docs/audit-report.md]

One check per listed item: the 4 taxonomies and the 12 controlled code lists. Exit status is 0 only when every audited
item passes.
"""
from __future__ import annotations

import argparse
import collections
import json
import sqlite3
import sys
from pathlib import Path

from etl.conformance import load_spec

CATALOG_STATUS = {"open": 450, "partially-solved": 369, "empirically-open": 227, "solved-but-impractical": 7}
MAX_UNRESOLVED = 0.10


class Graph:
    """All nodes and edges of a persisted candidate, read-only."""

    def __init__(self, path: Path):
        conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
        try:
            self.nodes = collections.defaultdict(list)
            self.by_id = {}
            for node_id, label, props in conn.execute("SELECT node_id,label,properties_json FROM nodes"):
                record = json.loads(props)
                self.nodes[label].append(record)
                self.by_id[node_id] = (label, record)
            self.edges = collections.defaultdict(list)
            for rel, src, dst, props in conn.execute("SELECT rel_type,source_id,target_id,properties_json FROM edges"):
                self.edges[rel].append((src, dst, json.loads(props)))
        finally:
            conn.close()

    def label(self, node_id):
        return self.by_id.get(node_id, (None, None))[0]


def _result(item, checks):
    """checks: list of (description, ok, measured)."""
    return {"item": item, "status": "PASS" if all(ok for _, ok, _ in checks) else "FAIL",
            "checks": [{"check": d, "ok": ok, "measured": m} for d, ok, m in checks]}


# --- taxonomies (4) ---------------------------------------------------------------

def audit_taxonomies(g: Graph, spec: dict) -> list[dict]:
    terms = {n["id"]: n for n in g.nodes["TaxonomyTerm"]}
    classified = collections.defaultdict(lambda: collections.defaultdict(list))
    for src, dst, props in g.edges["CLASSIFIED_AS"]:
        term = terms.get(dst, {})
        classified[term.get("scheme")][src].append((term, props))
    term_links = [e for rel, es in g.edges.items() for e in es
                  if g.label(e[0]) == "TaxonomyTerm" and g.label(e[1]) == "TaxonomyTerm"]

    def scheme(item, name, codes, members, code_of):
        scheme_terms = [t for t in terms.values() if t["scheme"] == name]
        term_codes = {t["code"] for t in scheme_terms}
        assigned = classified[name]
        one_each = sum(len(assigned.get(m["id"], [])) == 1 for m in members)
        wrong_code = sum(1 for m in members for t, _ in assigned.get(m["id"], []) if t["code"] != code_of(m))
        no_evidence = sum(1 for m in members for _, p in assigned.get(m["id"], []) if not p.get("evidence"))
        unresolved = sum(1 for m in members for _, p in assigned.get(m["id"], [])
                         if p.get("evidence_status") == "unresolved")
        share = unresolved / len(members) if members else 1.0
        notation = sum(1 for t in scheme_terms if t.get("notation") != t.get("code"))
        return _result(item, [
            ("terms equal the closed code list", term_codes == set(codes), f"{len(term_codes)} terms / {len(codes)} codes"),
            ("every member classified exactly once in the scheme", one_each == len(members) and members != [],
             f"{one_each}/{len(members)}"),
            ("assigned term matches the member's own code", wrong_code == 0, f"{wrong_code} mismatches"),
            ("every assignment carries evidence", no_evidence == 0, f"{no_evidence} without evidence"),
            ("every term has notation = code", notation == 0, f"{notation} wrong"),
            (f"unresolved share <= {MAX_UNRESOLVED:.0%}", share <= MAX_UNRESOLVED, f"{share:.1%}"),
            ("scheme is flat: no links between taxonomy terms", not term_links, f"{len(term_links)} links"),
        ])

    problems = g.nodes["Problem"]
    topics = sorted(g.nodes["Topic"], key=lambda t: t["number"])
    topic_ids = [t["id"] for t in topics]
    in_topic = collections.Counter(src for src, _, _ in g.edges["IN_TOPIC"])
    used = {p["topic_id"] for p in problems}
    numbering = [t["number"] for t in topics] == [f"{i:02d}" for i in range(1, 36)]
    topic = scheme("1. DBMS topic", "dbms-topic", topic_ids, problems, lambda p: p["topic_id"])
    topic["checks"] += [
        {"check": "35 topics numbered 01-35 as in TAXONOMY.md", "ok": numbering and len(topics) == 35,
         "measured": f"{len(topics)} topics"},
        {"check": "every problem has exactly one IN_TOPIC", "ok": all(in_topic[p["id"]] == 1 for p in problems),
         "measured": f"{sum(in_topic[p['id']] == 1 for p in problems)}/{len(problems)}"},
        {"check": "every topic has problems", "ok": used == set(topic_ids), "measured": f"{len(used)}/35"},
    ]
    topic["status"] = "PASS" if all(c["ok"] for c in topic["checks"]) else "FAIL"
    codes = spec["codes"]
    return [
        topic,
        scheme("2. Problem type", "problem-type", codes["Problem.problem_type"], problems,
               lambda p: p["problem_type"]),
        scheme("3. Solution/technique family", "solution-technique-family",
               codes["Algorithm.family|System.family"], g.nodes["Algorithm"] + g.nodes["System"],
               lambda n: n["family"]),
        scheme("4. Computational model/workload", "computation-model-workload",
               codes["ComputationModel.class"], g.nodes["ComputationModel"], lambda n: n["class"]),
    ]


# --- controlled code lists (12) -------------------------------------------------------

def audit_code_lists(g: Graph, spec: dict) -> list[dict]:
    codes = spec["codes"]

    def code_list(item, values, allowed, unknown=(), limit=None, extra=()):
        missing = sum(v in (None, "") for v in values)
        outside = sorted({v for v in values if v not in allowed and v not in (None, "")})
        counts = collections.Counter(values)
        share = sum(counts[u] for u in unknown) / len(values) if values else 1.0
        checks = [
            ("present on every record", missing == 0 and bool(values), f"{len(values) - missing}/{len(values)}"),
            ("every value is in the closed list", not outside, ", ".join(map(str, outside)) or "0 outside"),
        ]
        if limit is not None:
            checks.append((f"'{'/'.join(unknown)}' share <= {limit:.0%}", share <= limit, f"{share:.1%}"))
        checks.extend(extra)
        result = _result(item, checks)
        result["distribution"] = dict(counts.most_common())
        return result

    node = lambda label, key: [n.get(key) for n in g.nodes[label]]
    edge = lambda rel, key: [p.get(key) for _, _, p in g.edges[rel]]
    status = node("Problem", "status")
    gap_methods = node("Gap", "verdict_method")
    raw_kept = sum(1 for _, _, p in g.edges["CITES"] if p.get("role") in ("mixed", "unclassified") and "role_raw" in p)
    return [
        code_list("1. Problem.status", status, codes["Problem.status"],
                  extra=[("counts equal the catalog (450/369/227/7)",
                          dict(collections.Counter(status)) == CATALOG_STATUS, dict(collections.Counter(status)))]),
        code_list("2. CITES.role", edge("CITES", "role"), codes["CITES.role"], ("unclassified",), 0.02,
                  extra=[("raw tag kept for mixed/unclassified roles", raw_kept == sum(
                      1 for r in edge("CITES", "role") if r in ("mixed", "unclassified")), f"{raw_kept}")]),
        code_list("3. Gap.verdict", node("Gap", "verdict"), codes["Gap.verdict"], ("unstated",), 0.10,
                  extra=[("verdict_method in stated/keyword/none",
                          set(gap_methods) <= set(spec["property_values"]["Gap.verdict_method"]),
                          dict(collections.Counter(gap_methods)))]),
        code_list("4. Bound.kind", node("Bound", "kind"), codes["Bound.kind"], ("unclassified",), 0.05),
        code_list("5. STATE_OF_ART.kind", edge("STATE_OF_ART", "kind"), codes["STATE_OF_ART.kind"]),
        code_list("6. Person.name_form", node("Person", "name_form"), codes["Person.name_form"]),
        code_list("7. Venue.kind", node("Venue", "kind"), codes["Venue.kind"], ("other",), 0.25),
        code_list("8. Institution.kind", node("Institution", "kind"), codes["Institution.kind"]),
        code_list("9. Problem.problem_type", node("Problem", "problem_type"), codes["Problem.problem_type"],
                  ("unclassified",), 0.05),
        code_list("10. Algorithm.family / System.family", node("Algorithm", "family") + node("System", "family"),
                  codes["Algorithm.family|System.family"], ("unclassified",), 0.10),
        code_list("11. ComputationModel.class", node("ComputationModel", "class"), codes["ComputationModel.class"],
                  ("unclassified",), 0.0),
        code_list("12. CLASSIFIED_AS.evidence_status", edge("CLASSIFIED_AS", "evidence_status"),
                  codes["CLASSIFIED_AS.evidence_status"], ("unresolved",), 0.10),
    ]


PARTS = {"taxonomies": ("Taxonomies (4)", audit_taxonomies),
         "code-lists": ("Controlled code lists (12)", audit_code_lists)}


def run(path: Path, parts) -> dict:
    g, spec = Graph(path), load_spec()
    return {part: PARTS[part][1](g, spec) for part in parts}


def render(path: Path, results: dict) -> str:
    lines = ["# Standards audit", "",
             (f"Generated by `python -m etl.audit` for `{path.name}`, item by item against "
             "[standards.md](standards.md)."), ""]
    for part, items in results.items():
        title = PARTS[part][0]
        passed = sum(i["status"] == "PASS" for i in items)
        lines += [f"## {title}: {passed} of {len(items)} pass", "", "| Item | Status | Checks |", "|---|---|---|"]
        for i in items:
            checks = "; ".join(f"{'✓' if c['ok'] else '✗'} {c['check']} ({c['measured']})" for c in i["checks"])
            lines.append(f"| {i['item']} | {i['status']} | {checks} |")
        lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--part", choices=[*PARTS, "all"], default="all")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    parts = list(PARTS) if args.part == "all" else [args.part]
    results = run(args.graph, parts)
    for part, items in results.items():
        print(f"== {PARTS[part][0]}")
        for i in items:
            print(f"{i['status']:4}  {i['item']}")
            for c in i["checks"]:
                if not c["ok"]:
                    print(f"        FAILED: {c['check']} ({c['measured']})")
    if args.report:
        args.report.write_text(render(args.graph, results), encoding="utf-8")
    return 0 if all(i["status"] == "PASS" for items in results.values() for i in items) else 1


if __name__ == "__main__":
    sys.exit(main())
