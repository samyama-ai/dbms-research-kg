"""Item-by-item audit of a built graph against docs/standards.md.

    python -m etl.audit --graph build/dbms_research_kg.schema-candidate-v5.sqlite \
        --part taxonomies|code-lists|standards|all [--report docs/audit-report.md]

One check per listed item: the 4 taxonomies, the 12 controlled code lists and
the 6 standards/specification groups. Exit status is 0 only when every audited
item passes.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

from etl.conformance import ONTOLOGY_PATH, load_spec, validate_ontology
from etl.source_entities import CONCEPT_HIERARCHY

PINNED = "5fff7f74508a52ac238f3bb608b8c8c872489fec"
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


# --- standards / specification groups (6) ----------------------------------------------

def _iso_date(value):
    try:
        return date.fromisoformat(value).isoformat() == value
    except (TypeError, ValueError):
        return False


def audit_standards(g: Graph, spec: dict) -> list[dict]:
    all_nodes = [n for records in g.nodes.values() for n in records]
    all_edges = [p for records in g.edges.values() for _, _, p in records]
    prov_fields = spec["provenance_required"]
    missing_prov = sum(1 for n in all_nodes for f in prov_fields if n.get(f) in (None, ""))
    unpinned = sum(1 for n in all_nodes if n.get("source_path") and PINNED not in n.get("source_url", ""))
    edge_prov = sum(1 for p in all_edges for f in spec["relationship_provenance_required"] if p.get(f) in (None, ""))
    edge_commit = sum(1 for p in all_edges if p.get("source_commit") != PINNED)
    datasources = g.nodes["DataSource"]
    from_source = collections.Counter(src for src, _, _ in g.edges["FROM_SOURCE"])
    prov = _result("PROV-O", [
        ("every node has the provenance fields", missing_prov == 0, f"{missing_prov} missing"),
        ("page-derived nodes link the pinned commit", unpinned == 0, f"{unpinned} unpinned"),
        ("every edge has source, source_url, source_commit", edge_prov == 0, f"{edge_prov} missing"),
        ("every edge is pinned to the catalog commit", edge_commit == 0, f"{edge_commit} other"),
        ("one DataSource at the pinned version", len(datasources) == 1 and datasources[0]["version"] == PINNED,
         f"{len(datasources)}"),
        ("every Problem has FROM_SOURCE", all(from_source[p["id"]] == 1 for p in g.nodes["Problem"]),
         f"{len(from_source)}/{len(g.nodes['Problem'])}"),
    ])

    concepts = {n["id"]: n["name"] for n in g.nodes["Concept"]}
    hierarchy = [(concepts.get(s), concepts.get(d), p) for s, d, p in g.edges["GENERALIZES"]]
    listed = {(a, b) for a, b, _ in CONCEPT_HIERARCHY}
    terms = g.nodes["TaxonomyTerm"]
    skos = _result("SKOS", [
        ("taxonomy terms carry scheme and notation", all(t.get("scheme") and t.get("notation") for t in terms),
         f"{len(terms)} terms"),
        ("schemes are the four in the spec", {t["scheme"] for t in terms} == set(spec["taxonomy_schemes"]),
         sorted({t["scheme"] for t in terms})),
        ("broader links only between concepts", all(a and b for a, b, _ in hierarchy), f"{len(hierarchy)} links"),
        ("every broader link is an enumerated pair", all((a, b) in listed for a, b, _ in hierarchy),
         f"{sum((a, b) not in listed for a, b, _ in hierarchy)} not listed"),
        ("every broader link has a rationale", all(p.get("rationale") for _, _, p in hierarchy), ""),
        ("topic scheme is flat (no Topic hierarchy)", not any(
            g.label(s) == "Topic" and g.label(d) == "Topic" for es in g.edges.values() for s, d, _ in es), ""),
    ])

    ontology = validate_ontology()
    ttl = ONTOLOGY_PATH.read_text(encoding="utf-8")
    undeclared_classes = [lb for lb in spec["labels"] if not re.search(rf"^kg:{lb} a owl:Class\b", ttl, re.MULTILINE)]
    undeclared_props = [r for r in spec["relationships"]
                        if not re.search(rf"^kg:{r} a owl:ObjectProperty\b", ttl, re.MULTILINE)]
    rdf = _result("RDF/RDFS/OWL", [
        ("Turtle ontology parses and matches the inventory (rdflib)", ontology["status"] == "PASS",
         f"{ontology['status']}, {ontology.get('triple_count', '?')} triples"),
        ("every node label is an owl:Class", not undeclared_classes,
         ", ".join(undeclared_classes) or f"{len(spec['labels'])} declared"),
        ("every relationship type is an owl:ObjectProperty", not undeclared_props,
         ", ".join(undeclared_props) or f"{len(spec['relationships'])} declared"),
    ])

    papers = g.nodes["Paper"]
    parsed_no_title = sum(1 for p in papers if p.get("parse_status") == "parsed" and not p.get("title"))
    bad_year = sum(1 for p in papers if p.get("year") is not None and not isinstance(p["year"], int))
    no_position = sum(1 for _, _, p in g.edges["AUTHORED_BY"] if not isinstance(p.get("position"), int))
    dc = _result("Dublin Core / ISO 15836", [
        ("parsed papers have a title (dcterms:title)", parsed_no_title == 0, f"{parsed_no_title} missing"),
        ("years are integers (dcterms:issued)", bad_year == 0, f"{bad_year} not integer"),
        ("authorship edges have a position (dcterms:creator)", no_position == 0, f"{no_position} missing"),
        ("every problem has a subject topic (dcterms:subject)",
         len(g.edges["IN_TOPIC"]) == len(g.nodes["Problem"]), f"{len(g.edges['IN_TOPIC'])}"),
    ])

    dois = [(p["doi"], p.get("citation_text", "")) for p in papers if p.get("doi")]
    bad_syntax = sum(1 for d, _ in dois if not re.fullmatch(r"10\.\d{4,9}/\S+", d))
    invented = sum(1 for d, text in dois if d.casefold() not in text.casefold())
    doi = _result("ISO 26324 (DOI)", [
        ("DOI syntax 10.<4-9 digits>/<suffix>", bad_syntax == 0 and bool(dois), f"{len(dois)} DOIs, {bad_syntax} bad"),
        ("no DOI is synthesized: each occurs in its citation text", invented == 0, f"{invented} not in text"),
    ])

    bad_dates = sum(1 for n in all_nodes for f in ("retrieved_at", "source_date") if not _iso_date(n.get(f)))
    month_fields = ("first_added", "last_reviewed", "last_substantive_update")
    bad_months = sum(1 for p in g.nodes["Problem"] for f in month_fields
                     if p.get(f) and not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", p[f]))
    iso = _result("ISO 8601", [
        ("retrieved_at and source_date are full YYYY-MM-DD dates", bad_dates == 0, f"{bad_dates} bad"),
        ("page review dates keep YYYY-MM precision", bad_months == 0, f"{bad_months} bad"),
    ])
    return [prov, skos, rdf, dc, doi, iso]


PARTS = {"taxonomies": ("Taxonomies (4)", audit_taxonomies),
         "code-lists": ("Controlled code lists (12)", audit_code_lists),
         "standards": ("Standards/specification groups (6)", audit_standards)}


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
