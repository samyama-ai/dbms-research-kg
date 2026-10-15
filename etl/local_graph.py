"""Build and inspect an isolated SQLite property graph from the local snapshot.

The reference sgsnap is imported as read-only input. Duplicate typed endpoint
pairs in that export are collapsed while their source edge IDs and property
variants are retained. Additional relationships are derived only from the
pinned catalog and are tagged with source provenance.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import itertools
import json
import sqlite3
import sys
from pathlib import Path

from etl.citations import normalize_title, person_key
from etl.loader import PINNED_COMMIT, prepare

EXPECTED_SNAPSHOT_SHA256 = "82119412c26c0b0b186b0edab36d28a1c6632ec8b47905723fa7b9985880b155"
EXPECTED_LABELS = {
    "Algorithm", "Bound", "ComputationModel", "Concept", "FutureDirection",
    "Institution", "Paper", "Person", "Problem", "System", "Topic", "Venue",
}
EXPECTED_RELATIONSHIPS = {
    "ACTIVE_ON", "AFFILIATED_WITH", "APPEARED_AT", "AUTHORED_BY", "CITES",
    "CLOSING_REQUIRES", "GENERALIZES", "HAS_BOUND", "IN_MODEL", "IN_TOPIC",
    "RELATED_TO", "RESTS_ON", "STATE_OF_ART",
}
ENDPOINTS = {
    "ACTIVE_ON": {("Person", "Problem"), ("Institution", "Problem")},
    "AFFILIATED_WITH": {("Person", "Institution")},
    "APPEARED_AT": {("Paper", "Venue")},
    "AUTHORED_BY": {("Paper", "Person")},
    "CITES": {("Problem", "Paper")},
    "CLOSING_REQUIRES": {("Problem", "FutureDirection")},
    "GENERALIZES": {("Concept", "Concept")},
    "HAS_BOUND": {("Problem", "Bound")},
    "IN_MODEL": {("Bound", "ComputationModel")},
    "IN_TOPIC": {("Problem", "Topic")},
    "RELATED_TO": {("Problem", "Problem")},
    "RESTS_ON": {("Problem", "Concept")},
    "STATE_OF_ART": {("Problem", "Algorithm"), ("Problem", "System")},
}
REQUIRED_NODE_PROPERTIES = {
    "Problem": ("id", "title", "status", "topicNum", "statement", "workedExample"),
    "Topic": ("num", "name", "slug"),
    "Paper": ("id", "title"),
    "Person": ("name",), "Venue": ("name",), "Institution": ("name",),
    "Concept": ("name",), "Algorithm": ("name",), "System": ("name", "kind"),
    "Bound": ("id", "direction", "kind", "expr"),
    "ComputationModel": ("name",),
    "FutureDirection": ("id", "problem", "text"),
}
DEFAULT_SNAPSHOT = Path.home() / "dbms-research.sgsnap"
DEFAULT_CATALOG = Path("build/source_catalog.json")
DEFAULT_OUTPUT = Path("build/dbms_research_kg.sqlite")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _snapshot_records(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        try:
            header = json.loads(next(stream))
        except (StopIteration, json.JSONDecodeError) as exc:
            raise ValueError("Snapshot has no valid JSON header") from exc
        if header.get("format") != "sgsnap" or header.get("version") != 1:
            raise ValueError("Expected sgsnap version 1")
        if header.get("tenant") != "dbms-research":
            raise ValueError("Snapshot tenant is not dbms-research")
        if set(header.get("labels", [])) != EXPECTED_LABELS:
            raise ValueError("Snapshot node-label inventory does not match the reference schema")
        if set(header.get("edge_types", [])) != EXPECTED_RELATIONSHIPS:
            raise ValueError("Snapshot relationship inventory does not match the reference schema")
        yield header, None
        for line_no, line in enumerate(stream, 2):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid snapshot JSON on line {line_no}") from exc
            if record.get("t") not in {"n", "e"}:
                raise ValueError(f"Unknown snapshot record kind on line {line_no}")
            yield None, record


def _snapshot_edge_groups(snapshot: Path):
    header = None
    nodes = {}
    groups = collections.defaultdict(list)
    actual_node_count = actual_edge_count = 0
    label_counts = collections.Counter()
    type_counts = collections.Counter()
    for head, record in _snapshot_records(snapshot):
        if head is not None:
            header = head
            continue
        if record["t"] == "n":
            labels = record.get("labels", [])
            if len(labels) != 1 or labels[0] not in EXPECTED_LABELS:
                raise ValueError(f"Snapshot node {record.get('id')} must have exactly one known label")
            node_id = str(record["id"])
            if node_id in nodes:
                raise ValueError(f"Duplicate snapshot node id {node_id}")
            label = labels[0]
            props = record.get("props", {})
            logical_id = str(props.get("id", f"snapshot-node:{node_id}"))
            nodes[node_id] = (label, props, logical_id)
            label_counts[label] += 1
            actual_node_count += 1
        else:
            rel = record.get("type")
            if rel not in EXPECTED_RELATIONSHIPS:
                raise ValueError(f"Unknown relationship type {rel!r}")
            source_id, target_id = str(record["src"]), str(record["tgt"])
            if source_id not in nodes or target_id not in nodes:
                raise ValueError(f"Relationship {record.get('id')} has a missing endpoint")
            pair = (nodes[source_id][0], nodes[target_id][0])
            if pair not in ENDPOINTS[rel]:
                raise ValueError(f"{rel} endpoint labels {pair} violate the reference schema")
            groups[(rel, source_id, target_id)].append(record)
            type_counts[rel] += 1
            actual_edge_count += 1
    if header is None:
        raise ValueError("Snapshot is empty")
    if actual_node_count != header.get("node_count") or actual_edge_count != header.get("edge_count"):
        raise ValueError("Snapshot header counts do not match its actual records")
    if set(label_counts) != EXPECTED_LABELS or set(type_counts) != EXPECTED_RELATIONSHIPS:
        raise ValueError("Snapshot records do not populate the declared label/type inventory")
    return header, nodes, groups, label_counts, type_counts


def _open_or_create(path: Path, signature: str, snapshot_hash: str, catalog_hash: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    existed = path.exists()
    if existed:
        with path.open("rb") as stream:
            if stream.read(16) != b"SQLite format 3\x00":
                raise RuntimeError(f"Refusing to overwrite non-SQLite output: {path}")
        conn = sqlite3.connect(path)
        try:
            row = conn.execute("SELECT value FROM graph_metadata WHERE key='build_signature'").fetchone()
        except sqlite3.DatabaseError as exc:
            conn.close()
            raise RuntimeError(f"Existing SQLite file is not this builder's graph: {path}") from exc
        if row is None or row[0] != signature:
            conn.close()
            raise RuntimeError("Existing graph was built from different inputs; choose a new --output path")
        return conn

    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript("""
        CREATE TABLE graph_metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE nodes(
            node_id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            logical_id TEXT NOT NULL,
            properties_json TEXT NOT NULL,
            origin TEXT NOT NULL,
            source_reference TEXT NOT NULL,
            UNIQUE(label, logical_id)
        );
        CREATE INDEX nodes_by_label ON nodes(label);
        CREATE TABLE edges(
            edge_id TEXT PRIMARY KEY,
            rel_type TEXT NOT NULL,
            source_id TEXT NOT NULL REFERENCES nodes(node_id),
            target_id TEXT NOT NULL REFERENCES nodes(node_id),
            properties_json TEXT NOT NULL,
            origin TEXT NOT NULL,
            source_reference TEXT NOT NULL,
            UNIQUE(rel_type, source_id, target_id)
        );
        CREATE INDEX edges_by_type ON edges(rel_type);
        CREATE INDEX edges_by_source ON edges(source_id, rel_type);
        CREATE INDEX edges_by_target ON edges(target_id, rel_type);
    """)
    conn.executemany("INSERT INTO graph_metadata(key,value) VALUES(?,?)", [
        ("build_signature", signature), ("snapshot_sha256", snapshot_hash),
        ("catalog_sha256", catalog_hash), ("catalog_commit", PINNED_COMMIT),
        ("schema_labels", canonical_json(sorted(EXPECTED_LABELS))),
        ("schema_relationships", canonical_json(sorted(EXPECTED_RELATIONSHIPS))),
        ("build_state", "building"),
    ])
    conn.commit()
    return conn


def _insert_snapshot_nodes(conn, nodes):
    for node_id, (label, props, logical_id) in nodes.items():
        values = (node_id, label, logical_id, canonical_json(props), "snapshot", "sha256:" + conn.execute(
            "SELECT value FROM graph_metadata WHERE key='snapshot_sha256'").fetchone()[0])
        conn.execute("INSERT OR IGNORE INTO nodes VALUES(?,?,?,?,?,?)", values)
        existing = conn.execute("SELECT label,logical_id,properties_json FROM nodes WHERE node_id=?", (node_id,)).fetchone()
        if existing != values[1:4]:
            raise RuntimeError(f"Existing node {node_id} conflicts with snapshot data")


def _merged_snapshot_properties(records):
    properties = [x.get("props", {}) for x in records]
    serialized = sorted({canonical_json(x) for x in properties})
    base = json.loads(serialized[0])
    if len(serialized) > 1:
        common_keys = set.intersection(*(set(x) for x in properties)) if properties else set()
        base = {k: properties[0][k] for k in common_keys
                if all(canonical_json(x[k]) == canonical_json(properties[0][k]) for x in properties)}
        base["_source_property_variants"] = [json.loads(x) for x in serialized]
    if len(records) > 1:
        base["_source_snapshot_edge_ids"] = sorted(str(x["id"]) for x in records)
    return base


def _insert_edge(conn, rel, source, target, props, origin, source_reference, edge_id=None):
    if conn.execute("SELECT 1 FROM nodes WHERE node_id=?", (str(source),)).fetchone() is None:
        raise ValueError(f"Missing edge source endpoint {source}")
    if conn.execute("SELECT 1 FROM nodes WHERE node_id=?", (str(target),)).fetchone() is None:
        raise ValueError(f"Missing edge target endpoint {target}")
    if edge_id is None:
        edge_id = "derived:" + hashlib.sha256(
            f"{rel}\n{source}\n{target}".encode()).hexdigest()[:32]
    cursor = conn.execute("INSERT OR IGNORE INTO edges VALUES(?,?,?,?,?,?,?)",
                          (edge_id, rel, str(source), str(target), canonical_json(props), origin, source_reference))
    row = conn.execute("SELECT properties_json,origin,source_reference FROM edges WHERE rel_type=? AND source_id=? AND target_id=?",
                       (rel, str(source), str(target))).fetchone()
    if row is None:
        raise RuntimeError(f"Failed to persist {rel} edge {source}->{target}")
    if not cursor.rowcount and row != (canonical_json(props), origin, source_reference):
        raise RuntimeError(f"Rerun would change existing {rel} edge {source}->{target}")
    return cursor.rowcount == 1


def _make_catalog_maps(data, snapshot_nodes):
    indexes = collections.defaultdict(list)
    for node_id, (label, props, _) in snapshot_nodes.items():
        if label == "Problem":
            indexes[(label, "id", str(props.get("id", "")))].append(node_id)
        elif label == "Paper":
            indexes[(label, "title_year", normalize_title(props.get("title", "")), str(props.get("year", "")))].append(node_id)
        elif label == "Person":
            indexes[(label, "person_key", person_key(props.get("name", "")))].append(node_id)
        elif label in {"Venue", "Concept", "Algorithm", "System", "ComputationModel"}:
            indexes[(label, "name", str(props.get("name", "")).casefold())].append(node_id)

    def unique(key):
        values = indexes.get(key, [])
        return values[0] if len(values) == 1 else None

    maps = {label: {} for label in ("Problem", "Paper", "Person", "Venue", "Concept", "Algorithm", "System", "ComputationModel")}
    for problem in data["Problem"]:
        node_id = unique(("Problem", "id", problem["id"]))
        if node_id is not None:
            maps["Problem"][problem["id"]] = node_id
    for paper in data["Paper"]:
        title = normalize_title(paper.get("title", ""))
        if not title:
            continue
        node_id = unique(("Paper", "title_year", title, str(paper.get("year") or "")))
        if node_id is not None:
            maps["Paper"][paper["id"]] = node_id
    for label in ("Person", "Venue", "Concept", "Algorithm", "System", "ComputationModel"):
        for record in data.get(label, []):
            if label == "Person":
                key = (label, "person_key", person_key(record.get("name", "")))
            else:
                key = (label, "name", str(record.get("name", "")).casefold())
            node_id = unique(key)
            if node_id is not None:
                maps[label][record["id"]] = node_id
    return maps


def _add_catalog_edges(conn, data, maps, snapshot_nodes, snapshot_related):
    problem_records = {p["id"]: p for p in data["Problem"]}
    paper_records = {p["id"]: p for p in data["Paper"]}
    source_ref = f"https://github.com/samyama-ai/dbms_research/tree/{PINNED_COMMIT}"
    relation_configs = {
        "CITES": ("Problem", "problem_id", "Paper", "target_id"),
        "AUTHORED_BY": ("Paper", "paper_id", "Person", "target_id"),
        "APPEARED_AT": ("Paper", "paper_id", "Venue", "target_id"),
        "RESTS_ON": ("Problem", "problem_id", "Concept", "target_id"),
        "STATE_OF_ART": ("Problem", "problem_id", None, "target_id"),
    }
    additions = collections.Counter()
    for rel, (source_label, source_key, target_label, target_key) in relation_configs.items():
        for edge in data.get(rel, []):
            src = maps[source_label].get(edge.get(source_key))
            actual_target_label = edge.get("target_label") if target_label is None else target_label
            dst = maps.get(actual_target_label, {}).get(edge.get(target_key))
            if src is None or dst is None:
                continue
            src_node, dst_node = snapshot_nodes[src], snapshot_nodes[dst]
            if (src_node[0], dst_node[0]) not in ENDPOINTS[rel]:
                continue
            page = problem_records.get(edge.get("problem_id")) or paper_records.get(edge.get("paper_id"))
            # Skip relationships already represented in the snapshot, regardless
            # of its older edge properties, so pair uniqueness is retained.
            if conn.execute("SELECT 1 FROM edges WHERE rel_type=? AND source_id=? AND target_id=?",
                            (rel, src, dst)).fetchone():
                continue
            props = {k: v for k, v in edge.items()
                     if k not in {"id", "problem_id", "paper_id", "target_id", "source_label", "target_label"}}
            if page is not None:
                props.update({"source_path": page["source_path"], "source_commit": PINNED_COMMIT,
                              "source_url": f"https://github.com/samyama-ai/dbms_research/blob/{PINNED_COMMIT}/{page['source_path']}",
                              "method": "parsed"})
            if _insert_edge(conn, rel, src, dst, props, "pinned_catalog", source_ref):
                additions[rel] += 1

    # RELATED_TO is derived from identifiable shared evidence only. A pair must
    # share at least two distinct source papers/concepts; a single ubiquitous
    # survey citation is insufficient. One edge per unordered pair is oriented
    # by stable snapshot node ID, matching the one-direction graph convention.
    evidence = collections.defaultdict(set)
    page_ids = collections.defaultdict(set)
    for edge in data["CITES"]:
        problem_node = maps["Problem"].get(edge["problem_id"])
        paper_node = maps["Paper"].get(edge["target_id"])
        if problem_node is not None and paper_node is not None:
            evidence[problem_node].add(("paper", paper_node))
            page_ids[problem_node].add(edge["problem_id"])
    for edge in data["RESTS_ON"]:
        problem_node = maps["Problem"].get(edge["problem_id"])
        concept_node = maps["Concept"].get(edge["target_id"])
        if problem_node is not None and concept_node is not None:
            evidence[problem_node].add(("concept", concept_node))
            page_ids[problem_node].add(edge["problem_id"])
    inverse = collections.defaultdict(list)
    for problem_node, items in evidence.items():
        for item in items:
            inverse[item].append(problem_node)
    common = collections.defaultdict(set)
    for item, problem_nodes in inverse.items():
        for a, b in itertools.combinations(sorted(set(problem_nodes), key=int), 2):
            common[(a, b)].add(item)
    for (a, b), shared in common.items():
        if len(shared) < 2 or frozenset((a, b)) in snapshot_related:
            continue
        union = evidence[a] | evidence[b]
        common_papers = sum(kind == "paper" for kind, _ in shared)
        common_concepts = sum(kind == "concept" for kind, _ in shared)
        paths = sorted({problem_records[p]["source_path"]
                        for node in (a, b) for p in page_ids[node] if p in problem_records})
        page_urls = [f"https://github.com/samyama-ai/dbms_research/blob/{PINNED_COMMIT}/{x}" for x in paths]
        props = {
            "method": "shared-papers-concepts",
            "score": round(len(shared) / len(union), 6),
            "shared_evidence_count": len(shared),
            "shared_papers": common_papers,
            "shared_concepts": common_concepts,
            "source_commit": PINNED_COMMIT,
            "source_urls": page_urls,
        }
        if _insert_edge(conn, "RELATED_TO", a, b, props, "pinned_catalog", "|".join(page_urls)):
            additions["RELATED_TO"] += 1
    return additions


def build(snapshot: Path, catalog_path: Path, output: Path) -> dict:
    for path in (snapshot, catalog_path):
        if not path.is_file():
            raise FileNotFoundError(f"Required build input is missing: {path}")
    snapshot_hash = sha256(snapshot)
    if snapshot_hash != EXPECTED_SNAPSHOT_SHA256:
        raise ValueError(f"Snapshot checksum mismatch: {snapshot_hash}")
    catalog_hash = sha256(catalog_path)
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if catalog.get("source", {}).get("actual_commit") != PINNED_COMMIT:
        raise ValueError(f"Catalog must be pinned to {PINNED_COMMIT}")
    if catalog.get("counts", {}).get("problem_pages") != 1053:
        raise ValueError("Pinned catalog does not contain the expected 1,053 problem pages")
    header, nodes, edge_groups, _, _ = _snapshot_edge_groups(snapshot)
    data = prepare(catalog)
    signature = hashlib.sha256(f"{snapshot_hash}\n{catalog_hash}\nlocal-graph-v1".encode()).hexdigest()
    conn = _open_or_create(output, signature, snapshot_hash, catalog_hash)
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        for offset in range(0, len(nodes), 500):
            _insert_snapshot_nodes(conn, dict(itertools.islice(nodes.items(), offset, offset + 500)))
            conn.commit()
        for offset, ((rel, src, dst), records) in enumerate(sorted(edge_groups.items()), 1):
            props = _merged_snapshot_properties(records)
            representative = min(records, key=lambda x: int(x["id"]))
            _insert_edge(conn, rel, src, dst, props, "snapshot", "sha256:" + snapshot_hash,
                         edge_id="snapshot:" + str(representative["id"]))
            if offset % 500 == 0:
                conn.commit()
        conn.commit()
        maps = _make_catalog_maps(data, nodes)
        snapshot_related = {frozenset((src, dst)) for rel, src, dst in edge_groups if rel == "RELATED_TO"}
        additions = _add_catalog_edges(conn, data, maps, nodes, snapshot_related)
        conn.commit()
        conn.execute("UPDATE graph_metadata SET value='complete' WHERE key='build_state'")
        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        raise
    conn.close()
    result = inspect(output, verify=True)
    result["snapshot_header"] = header
    result["catalog_edge_additions"] = dict(sorted(additions.items()))
    return result


def inspect(path: Path, *, verify: bool = False) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Local graph artifact not found: {path}")
    conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    try:
        metadata = dict(conn.execute("SELECT key,value FROM graph_metadata"))
        node_counts = dict(conn.execute("SELECT label,count(*) FROM nodes GROUP BY label ORDER BY label"))
        edge_counts = dict(conn.execute("SELECT rel_type,count(*) FROM edges GROUP BY rel_type ORDER BY rel_type"))
        nodes = conn.execute("SELECT count(*) FROM nodes").fetchone()[0]
        edges = conn.execute("SELECT count(*) FROM edges").fetchone()[0]
        duplicate_nodes = conn.execute("SELECT count(*) FROM (SELECT label,logical_id FROM nodes GROUP BY label,logical_id HAVING count(*)>1)").fetchone()[0]
        duplicate_edges = conn.execute("SELECT count(*) FROM (SELECT rel_type,source_id,target_id FROM edges GROUP BY rel_type,source_id,target_id HAVING count(*)>1)").fetchone()[0]
        fk_errors = list(conn.execute("PRAGMA foreign_key_check"))
        endpoint_errors = []
        for rel, source_label, target_label in conn.execute(
            "SELECT e.rel_type,s.label,t.label FROM edges e JOIN nodes s ON s.node_id=e.source_id JOIN nodes t ON t.node_id=e.target_id"):
            if (source_label, target_label) not in ENDPOINTS[rel]:
                endpoint_errors.append((rel, source_label, target_label))
        missing_properties = {}
        for label, required in REQUIRED_NODE_PROPERTIES.items():
            rows = [json.loads(row[0]) for row in conn.execute(
                "SELECT properties_json FROM nodes WHERE label=?", (label,))]
            missing_properties[label] = {
                key: sum(key not in props or props[key] in (None, "") for props in rows)
                for key in required
            }
        provenance_errors = 0
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
        actual_labels, actual_rels = set(node_counts), set(edge_counts)
        if verify:
            if metadata.get("build_state") != "complete":
                raise ValueError("Graph build is incomplete; rerun the same build command to resume")
            if actual_labels != EXPECTED_LABELS or actual_rels != EXPECTED_RELATIONSHIPS:
                raise ValueError("Persisted graph label/type inventory does not match reference schema")
            if sum(node_counts.values()) != nodes or sum(edge_counts.values()) != edges:
                raise ValueError("Per-label/type counts do not sum to persisted totals")
            if (duplicate_nodes or duplicate_edges or fk_errors or endpoint_errors
                    or provenance_errors or any(any(v for v in fields.values())
                                                 for fields in missing_properties.values())):
                raise ValueError("Persisted graph integrity checks failed")
            if nodes < 20_000 or edges < 39_400:
                raise ValueError(f"Persisted graph misses requested minimum: {nodes} nodes, {edges} edges")
        return {
            "path": str(path.resolve()), "storage": "SQLite property graph",
            "build_state": metadata.get("build_state"),
            "node_count": nodes, "edge_count": edges,
            "node_counts_sum": sum(node_counts.values()),
            "edge_counts_sum": sum(edge_counts.values()),
            "node_counts": dict(sorted(node_counts.items())),
            "edge_counts": dict(sorted(edge_counts.items())),
            "label_count": len(actual_labels), "relationship_type_count": len(actual_rels),
            "duplicate_logical_nodes": duplicate_nodes,
            "duplicate_logical_relationships": duplicate_edges,
            "foreign_key_errors": len(fk_errors), "endpoint_type_errors": len(endpoint_errors),
            "provenance_errors": provenance_errors,
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
                "related_problems": [{"problem": {k: (value := json.loads(p)).get(k)
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
