"""Build and inspect an isolated SQLite property graph from the local snapshot.

The reference sgsnap is imported as read-only input. Duplicate typed endpoint
pairs in that export are collapsed while their source edge IDs and property
variants are retained. Additional relationships are derived only from the
pinned catalog and are tagged with source provenance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

from etl.conformance import load_spec as load_conformance_spec
from etl.conformance import validate as validate_conformance
from etl.conformance import validate_ontology, validate_sqlite_alignments
from etl.loader import PINNED_COMMIT, prepare

EXPECTED_SNAPSHOT_SHA256 = "82119412c26c0b0b186b0edab36d28a1c6632ec8b47905723fa7b9985880b155"
from etl.snapshot_graph import (  # noqa: F401  (re-exported)
    DEFAULT_CATALOG,
    DEFAULT_CATALOG_OUTPUT,
    DEFAULT_OUTPUT,
    DEFAULT_SNAPSHOT,
    ENDPOINTS,
    EXPECTED_LABELS,
    EXPECTED_RELATIONSHIPS,
    REQUIRED_NODE_PROPERTIES,
    build,
    canonical_json,
    sha256,
)


def _candidate_data(conn, spec):
    data = {label: [] for label in spec["labels"]}
    data.update({rel: [] for rel in spec["relationships"]})
    for label, props in conn.execute("SELECT label,properties_json FROM nodes"):
        data[label].append(json.loads(props))
    for rel, props in conn.execute("SELECT rel_type,properties_json FROM edges"):
        data[rel].append(json.loads(props))
    return data


def _candidate_source_id(rel, edge):
    for key in ("source_node_id", "problem_id", "paper_id", "bound_id",
                "person_id", "institution_id"):
        if edge.get(key):
            return edge[key]
    raise ValueError(f"{rel} edge has no source node ID: {edge.get('id')}")


def _catalog_candidate_rows(data, spec):
    """Return exact persisted rows expected from this catalog/schema pair."""
    nodes = []
    for label in spec["labels"]:
        for node in data[label]:
            node_id = node["id"]
            origin = "project_schema" if node.get("source") == "project_schema" else "pinned_catalog"
            nodes.append((node_id, label, node_id, canonical_json(node), origin,
                          node.get("source_url", "")))
    edges = []
    for rel in sorted(spec["relationships"]):
        for edge in data[rel]:
            source_id = str(_candidate_source_id(rel, edge))
            target_id = str(edge.get("target_id", ""))
            edges.append((f"{rel}:{edge['id']}", rel, source_id, target_id,
                          canonical_json(edge), "pinned_catalog", edge.get("source_url", "")))
    return sorted(nodes), sorted(edges)


def build_catalog_candidate(catalog_path: Path, output: Path) -> dict:
    """Materialize only pinned-catalog/schema records to a new SQLite artifact.

    The existing snapshot graph is never opened for writing or used as candidate
    data: its per-record source lineage is insufficient for the v1 source-only
    boundary. Existing outputs resume on a matching signature. If the signature
    changes, persisted rows must exactly match freshly prepared catalog output
    before only schema/build metadata is refreshed; unrelated or divergent files
    are refused.
    """
    if not catalog_path.is_file():
        raise FileNotFoundError(f"Required catalog is missing: {catalog_path}")
    spec = load_conformance_spec()
    catalog_hash = sha256(catalog_path)
    spec_path = Path(__file__).resolve().parents[1] / "schema" / "conformance.json"
    ontology_path = spec_path.parent / "dbms_research_kg.ttl"
    schema_hash = sha256(spec_path)
    ontology_hash = sha256(ontology_path)
    root = Path(__file__).resolve().parents[1]
    implementation_hashes = {
        name: sha256(root / name)
        for name in ("etl/loader.py", "etl/citations.py", "etl/conformance.py", "etl/local_graph.py",
                     "etl/records.py", "etl/finalize.py", "etl/source_entities.py")
    }
    implementation_hash = hashlib.sha256(canonical_json(implementation_hashes).encode()).hexdigest()
    signature = hashlib.sha256(
        f"catalog-v1\n{catalog_hash}\n{schema_hash}\n{ontology_hash}\n{implementation_hash}".encode()).hexdigest()
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if catalog.get("source", {}).get("actual_commit") != PINNED_COMMIT:
        raise ValueError(f"Catalog must be pinned to {PINNED_COMMIT}")
    if catalog.get("counts", {}).get("problem_pages") != 1053:
        raise ValueError("Pinned catalog does not contain the expected 1,053 problem pages")
    data = prepare(catalog)
    validate_conformance(data)

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        with output.open("rb") as stream:
            file_header = stream.read(16)
        if file_header != b"SQLite format 3\x00":
            raise RuntimeError(f"Refusing to overwrite non-SQLite candidate path: {output}")
        conn = sqlite3.connect(output)
        try:
            metadata = dict(conn.execute("SELECT key,value FROM graph_metadata"))
        except sqlite3.DatabaseError as exc:
            conn.close()
            raise RuntimeError(f"Refusing to overwrite unrelated SQLite file: {output}") from exc
        if metadata.get("graph_kind") != "catalog-schema-v1":
            conn.close()
            raise RuntimeError("Candidate path belongs to different inputs; choose a new --output path")
        if metadata.get("build_signature") != signature:
            expected_nodes, expected_edges = _catalog_candidate_rows(data, spec)
            actual_nodes = sorted(conn.execute(
                "SELECT node_id,label,logical_id,properties_json,origin,source_reference FROM nodes"))
            actual_edges = sorted(conn.execute(
                "SELECT edge_id,rel_type,source_id,target_id,properties_json,origin,source_reference FROM edges"))
            if (metadata.get("catalog_sha256") != catalog_hash
                    or actual_nodes != expected_nodes or actual_edges != expected_edges):
                conn.close()
                raise RuntimeError(
                    "Existing candidate content differs from current pinned catalog output; refusing to refresh")
            try:
                conn.execute("BEGIN IMMEDIATE")
                updates = {
                    "build_signature": signature,
                    "schema_sha256": schema_hash,
                    "ontology_sha256": ontology_hash,
                    "implementation_sha256": implementation_hash,
                    "schema_labels": canonical_json(spec["labels"]),
                    "schema_relationships": canonical_json(sorted(spec["relationships"])),
                }
                conn.executemany("UPDATE graph_metadata SET value=? WHERE key=?",
                                 [(value, key) for key, value in updates.items()])
                conn.commit()
            except Exception:
                conn.rollback()
                conn.close()
                raise
    else:
        conn = sqlite3.connect(output)
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript("""
            CREATE TABLE graph_metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE nodes(
                node_id TEXT PRIMARY KEY, label TEXT NOT NULL, logical_id TEXT NOT NULL,
                properties_json TEXT NOT NULL, origin TEXT NOT NULL, source_reference TEXT NOT NULL,
                UNIQUE(label, logical_id));
            CREATE INDEX nodes_by_label ON nodes(label);
            CREATE TABLE edges(
                edge_id TEXT PRIMARY KEY, rel_type TEXT NOT NULL,
                source_id TEXT NOT NULL REFERENCES nodes(node_id),
                target_id TEXT NOT NULL REFERENCES nodes(node_id),
                properties_json TEXT NOT NULL, origin TEXT NOT NULL, source_reference TEXT NOT NULL,
                UNIQUE(rel_type, source_id, target_id));
            CREATE INDEX edges_by_type ON edges(rel_type);
            CREATE INDEX edges_by_source ON edges(source_id, rel_type);
            CREATE INDEX edges_by_target ON edges(target_id, rel_type);
        """)
        conn.executemany("INSERT INTO graph_metadata(key,value) VALUES(?,?)", [
            ("graph_kind", "catalog-schema-v1"), ("build_signature", signature),
            ("catalog_sha256", catalog_hash), ("catalog_commit", PINNED_COMMIT),
            ("schema_sha256", schema_hash), ("ontology_sha256", ontology_hash),
            ("implementation_sha256", implementation_hash),
            ("schema_labels", canonical_json(spec["labels"])),
            ("schema_relationships", canonical_json(sorted(spec["relationships"]))),
            ("build_state", "building"),
        ])
        conn.commit()

    conn.execute("PRAGMA foreign_keys=ON")
    endpoint_map = spec["relationships"]
    try:
        conn.execute("BEGIN IMMEDIATE")
        for label in spec["labels"]:
            for node in data[label]:
                node_id = node["id"]
                origin = "project_schema" if node.get("source") == "project_schema" else "pinned_catalog"
                reference = node.get("source_url", "")
                values = (node_id, label, node_id, canonical_json(node), origin, reference)
                conn.execute("INSERT OR IGNORE INTO nodes VALUES(?,?,?,?,?,?)", values)
                existing = conn.execute(
                    "SELECT node_id,label,logical_id,properties_json,origin,source_reference "
                    "FROM nodes WHERE node_id=?", (node_id,)).fetchone()
                if existing != values:
                    raise RuntimeError(f"Candidate node identity conflicts on rerun: {label}:{node_id}")
        node_labels = {node_id: label for label, records in data.items()
                       if label in spec["labels"] for node_id in (x["id"] for x in records)}
        for rel in sorted(spec["relationships"]):
            source_labels = set(endpoint_map[rel][0].split("|"))
            target_labels = set(endpoint_map[rel][1].split("|"))
            for edge in data[rel]:
                source_id = str(_candidate_source_id(rel, edge))
                target_id = str(edge.get("target_id", ""))
                if node_labels.get(source_id) not in source_labels:
                    raise ValueError(f"{rel} source {source_id} has wrong/missing node label")
                if node_labels.get(target_id) not in target_labels:
                    raise ValueError(f"{rel} target {target_id} has wrong/missing node label")
                edge_id = f"{rel}:{edge['id']}"
                values = (edge_id, rel, source_id, target_id, canonical_json(edge),
                          "pinned_catalog", edge.get("source_url", ""))
                conn.execute("INSERT OR IGNORE INTO edges VALUES(?,?,?,?,?,?,?)", values)
                existing = conn.execute(
                    "SELECT edge_id,rel_type,source_id,target_id,properties_json,origin,source_reference "
                    "FROM edges WHERE rel_type=? AND source_id=? AND target_id=?",
                    (rel, source_id, target_id)).fetchone()
                if existing != values:
                    raise RuntimeError(f"Candidate relationship conflicts on rerun: {rel}:{source_id}->{target_id}")
        conn.execute("UPDATE graph_metadata SET value='complete' WHERE key='build_state'")
        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        raise
    conn.close()
    return inspect(output, verify=True)


def inspect(path: Path, *, verify: bool = False) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Local graph artifact not found: {path}")
    conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    try:
        metadata = dict(conn.execute("SELECT key,value FROM graph_metadata"))
        candidate = metadata.get("graph_kind") == "catalog-schema-v1"
        spec = load_conformance_spec() if candidate else None
        expected_labels = set(spec["labels"]) if candidate else EXPECTED_LABELS
        expected_rels = set(spec["relationships"]) if candidate else EXPECTED_RELATIONSHIPS
        raw_node_counts = dict(conn.execute("SELECT label,count(*) FROM nodes GROUP BY label ORDER BY label"))
        raw_edge_counts = dict(conn.execute("SELECT rel_type,count(*) FROM edges GROUP BY rel_type ORDER BY rel_type"))
        node_counts = {label: raw_node_counts.get(label, 0) for label in sorted(expected_labels)}
        edge_counts = {rel: raw_edge_counts.get(rel, 0) for rel in sorted(expected_rels)}
        nodes = conn.execute("SELECT count(*) FROM nodes").fetchone()[0]
        edges = conn.execute("SELECT count(*) FROM edges").fetchone()[0]
        sqlite_integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        duplicate_nodes = conn.execute("SELECT count(*) FROM (SELECT label,logical_id FROM nodes GROUP BY label,logical_id HAVING count(*)>1)").fetchone()[0]
        duplicate_edges = conn.execute("SELECT count(*) FROM (SELECT rel_type,source_id,target_id FROM edges GROUP BY rel_type,source_id,target_id HAVING count(*)>1)").fetchone()[0]
        fk_errors = list(conn.execute("PRAGMA foreign_key_check"))
        endpoint_errors = []
        endpoint_contracts = {
            rel: {(source, target) for source in endpoints[0].split("|")
                  for target in endpoints[1].split("|")}
            for rel, endpoints in spec["relationships"].items()
        } if candidate else ENDPOINTS
        for rel, source_label, target_label in conn.execute(
            "SELECT e.rel_type,s.label,t.label FROM edges e JOIN nodes s ON s.node_id=e.source_id JOIN nodes t ON t.node_id=e.target_id"):
            if (source_label, target_label) not in endpoint_contracts.get(rel, set()):
                endpoint_errors.append((rel, source_label, target_label))
        missing_properties = {}
        property_contract = ({label: tuple(value["required"])
                              for label, value in spec["node_properties"].items()}
                             if candidate else REQUIRED_NODE_PROPERTIES)
        for label, required in property_contract.items():
            rows = [json.loads(row[0]) for row in conn.execute(
                "SELECT properties_json FROM nodes WHERE label=?", (label,))]
            missing_properties[label] = {
                key: sum(key not in props or props[key] in (None, "") for props in rows)
                for key in required
            }
        provenance_errors = 0
        if candidate:
            for props_json, origin, reference in conn.execute(
                    "SELECT properties_json,origin,source_reference FROM nodes"):
                props = json.loads(props_json)
                expected_origin = "project_schema" if props.get("source") == "project_schema" else "pinned_catalog"
                if origin != expected_origin or reference != props.get("source_url"):
                    provenance_errors += 1
            for props_json, origin, reference in conn.execute(
                    "SELECT properties_json,origin,source_reference FROM edges"):
                props = json.loads(props_json)
                if (origin != "pinned_catalog" or reference != props.get("source_url")
                        or props.get("source_commit") != PINNED_COMMIT):
                    provenance_errors += 1
            data_errors = validate_conformance(_candidate_data(conn, spec), raise_on_error=False)
        else:
            node_sources = conn.execute("SELECT origin,source_reference FROM nodes").fetchall()
            for origin, reference in node_sources:
                if origin != "snapshot" or reference != "sha256:" + metadata.get("snapshot_sha256", ""):
                    provenance_errors += 1
            for props_json, origin, reference in conn.execute(
                    "SELECT properties_json,origin,source_reference FROM edges"):
                if origin == "snapshot":
                    if reference != "sha256:" + metadata.get("snapshot_sha256", ""):
                        provenance_errors += 1
                elif origin == "pinned_catalog":
                    props = json.loads(props_json)
                    if props.get("source_commit") != PINNED_COMMIT or not (
                            props.get("source_url") or props.get("source_urls")):
                        provenance_errors += 1
                else:
                    provenance_errors += 1
            data_errors = []
        ontology_validation = validate_ontology()
        alignment_validation = validate_sqlite_alignments(path)
        actual_labels, actual_rels = set(raw_node_counts), set(raw_edge_counts)
        if verify:
            if metadata.get("build_state") != "complete":
                raise ValueError("Graph build is incomplete; rerun the same build command to resume")
            if candidate:
                declared_labels = set(json.loads(metadata.get("schema_labels", "[]")))
                declared_rels = set(json.loads(metadata.get("schema_relationships", "[]")))
                if (declared_labels != expected_labels or declared_rels != expected_rels
                        or actual_labels - expected_labels or actual_rels - expected_rels):
                    raise ValueError("Persisted graph label/type inventory does not match schema")
            elif actual_labels != expected_labels or actual_rels != expected_rels:
                raise ValueError("Persisted graph label/type inventory does not match reference schema")
            if sum(node_counts.values()) != nodes or sum(edge_counts.values()) != edges:
                raise ValueError("Per-label/type counts do not sum to persisted totals")
            if (duplicate_nodes or duplicate_edges or fk_errors or endpoint_errors
                    or provenance_errors or data_errors or any(any(v for v in fields.values())
                                                 for fields in missing_properties.values())):
                raise ValueError("Persisted graph integrity checks failed")
            if sqlite_integrity != "ok":
                raise ValueError(f"SQLite integrity check failed: {sqlite_integrity}")
            if not candidate and (nodes < 20_000 or edges < 39_400):
                raise ValueError(f"Persisted graph misses requested minimum: {nodes} nodes, {edges} edges")
            if candidate and ontology_validation["status"] == "FAIL":
                raise ValueError("Turtle ontology semantic validation failed")
        return {
            "path": str(path.resolve()), "storage": "SQLite property graph",
            "build_state": metadata.get("build_state"),
            "node_count": nodes, "edge_count": edges,
            "node_counts_sum": sum(node_counts.values()),
            "edge_counts_sum": sum(edge_counts.values()),
            "node_counts": dict(sorted(node_counts.items())),
            "edge_counts": dict(sorted(edge_counts.items())),
            "label_count": len(expected_labels), "relationship_type_count": len(expected_rels),
            "populated_label_count": len(raw_node_counts),
            "populated_relationship_type_count": len(raw_edge_counts),
            "duplicate_logical_nodes": duplicate_nodes,
            "duplicate_logical_relationships": duplicate_edges,
            "foreign_key_errors": len(fk_errors), "endpoint_type_errors": len(endpoint_errors),
            "sqlite_integrity_check": sqlite_integrity,
            "provenance_errors": provenance_errors,
            "schema_data_errors": len(data_errors),
            "ontology_validation": ontology_validation,
            "alignment_validation": alignment_validation["alignments"],
            "full_ontology_conformance": all(
                item["status"] == "PASS" for item in alignment_validation["alignments"].values()),
            "missing_required_node_properties": missing_properties,
        }
    finally:
        conn.close()


def traverse(path: Path, problem_id: str, limit: int = 5) -> dict:
    conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    try:
        problem = conn.execute("SELECT node_id,properties_json FROM nodes WHERE label='Problem' AND json_extract(properties_json,'$.id')=?", (problem_id,)).fetchone()
        if not problem:
            raise ValueError(f"Problem not found: {problem_id}")
        node_id, properties = problem
        problem_props = json.loads(properties)
        cited = conn.execute("""
            SELECT p.node_id, p.properties_json
            FROM edges c JOIN nodes p ON p.node_id=c.target_id AND p.label='Paper'
            WHERE c.rel_type='CITES' AND c.source_id=? LIMIT ?
        """, (node_id, limit)).fetchall()
        rows = []
        for paper_node_id, paper_json in cited:
            paper = json.loads(paper_json)
            authors = []
            for author_node_id, author_json in conn.execute(
                "SELECT n.node_id, n.properties_json FROM edges e "
                "JOIN nodes n ON n.node_id=e.target_id "
                "WHERE e.rel_type='AUTHORED_BY' AND e.source_id=? "
                "ORDER BY CAST(json_extract(e.properties_json, '$.prop') AS INTEGER), n.node_id",
                (paper_node_id,),
            ):
                author = json.loads(author_json)
                # Snapshot Person records often have no `id` property. Their
                # SQLite node_id is still a stable, unique graph key.
                authors.append({"id": author.get("id") or author_node_id,
                                "name": author.get("name")})
            rows.append({"paper": {k: paper.get(k) for k in ("id", "title", "year", "venue", "url")},
                         "authors": authors})
        related = conn.execute("""
            SELECT n.properties_json,e.properties_json FROM edges e
            JOIN nodes n ON n.node_id=e.target_id AND n.label='Problem'
            WHERE e.rel_type='RELATED_TO' AND e.source_id=? ORDER BY e.properties_json LIMIT ?
        """, (node_id, limit)).fetchall()
        return {"problem": {k: problem_props.get(k) for k in ("id", "title", "status")},
                "cited_papers_and_authors": rows,
                "related_problems": [{"problem": {k: json.loads(p).get(k)
                                                        for k in ("id", "title", "status")},
                                      "edge": json.loads(e)} for p, e in related]}
    finally:
        conn.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build", help="build/resume the local SQLite property graph")
    build_parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    build_parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    build_parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    catalog_build_parser = sub.add_parser(
        "build-catalog-candidate",
        help="materialize a separate v1 schema candidate from the pinned catalog only")
    catalog_build_parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    catalog_build_parser.add_argument("--output", type=Path, default=DEFAULT_CATALOG_OUTPUT)
    for name in ("inspect", "verify"):
        command = sub.add_parser(name)
        command.add_argument("--graph", type=Path, default=DEFAULT_OUTPUT)
    traverse_parser = sub.add_parser("traverse", help="follow Problem→Paper→Person and RELATED_TO edges")
    traverse_parser.add_argument("--graph", type=Path, default=DEFAULT_OUTPUT)
    traverse_parser.add_argument("--problem", required=True)
    traverse_parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            result = build(args.snapshot, args.catalog, args.output)
        elif args.command == "build-catalog-candidate":
            result = build_catalog_candidate(args.catalog, args.output)
        elif args.command == "inspect":
            result = inspect(args.graph)
        elif args.command == "verify":
            result = inspect(args.graph, verify=True)
        else:
            if args.limit < 1 or args.limit > 100:
                parser.error("--limit must be between 1 and 100")
            result = traverse(args.graph, args.problem, args.limit)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError, RuntimeError, sqlite3.DatabaseError) as exc:
        print(f"Local graph {args.command} failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
