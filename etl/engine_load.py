"""Write prepared records to a Samyama engine, and the `python -m etl.loader` command line."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

from samyama import SamyamaClient

from etl.citations import paper_identity, parse_citation
from etl.records import PINNED_COMMIT, chunks, cypher_map


def print_plan(data):
    print("=== Load plan ===")
    from etl.conformance import load_spec
    for label in load_spec()["labels"]:
        print(f"{label:18} {len(data[label]):>7,} nodes")
    print()
    for rel in load_spec()["relationships"]:
        print(f"{rel:18} {len(data[rel]):>7,} relationships")
    labels = tuple(load_spec()["labels"])
    relationships = tuple(load_spec()["relationships"])
    print(f"\n{'TOTAL':18} {sum(len(data[x]) for x in labels):>7,} planned node records")
    print(f"{'TOTAL':18} {sum(len(data[x]) for x in relationships):>7,} planned edge records")
    print("\nCitation metadata is parsed from source text and retains the raw citation; "
          "source parsing is not independent bibliographic verification.")


def create_nodes(client, label, records, batch_size):
    if not records:
        return
    for batch in chunks(records, batch_size):
        rows = "[" + ", ".join(cypher_map(row) for row in batch) + "]"
        query = (f"UNWIND {rows} AS row MERGE (n:{label} {{id: row.id}}) "
                 f"SET n += row")
        client.query(query)


def create_relationships(client, rel_type, records, batch_size):
    if not records:
        return
    if rel_type == "STATE_OF_ART" and len({r["target_label"] for r in records}) > 1:
        for label in ("Algorithm", "System"):
            typed = [r for r in records if r["target_label"] == label]
            if typed:
                create_relationships(client, rel_type, typed, batch_size)
        if any(r["target_label"] not in {"Algorithm", "System"} for r in records):
            raise ValueError("STATE_OF_ART has an unsupported target label")
        return
    if rel_type == "CLASSIFIED_AS" and len({r["source_label"] for r in records}) > 1:
        for label in {r["source_label"] for r in records}:
            create_relationships(client, rel_type,
                                 [r for r in records if r["source_label"] == label], batch_size)
        return
    if rel_type == "ACTIVE_ON" and len({r["source_label"] for r in records}) > 1:
        for label in {r["source_label"] for r in records}:
            create_relationships(client, rel_type,
                                 [r for r in records if r["source_label"] == label], batch_size)
        return
    if rel_type == "IN_TOPIC":
        source_label, target_label = "Problem", "Topic"
    elif rel_type == "HAS_BOUND":
        source_label, target_label = "Problem", "Bound"
    elif rel_type == "CLOSING_REQUIRES":
        source_label, target_label = "Problem", "FutureDirection"
    elif rel_type == "CITES":
        source_label, target_label = "Problem", "Paper"
    elif rel_type == "AUTHORED_BY":
        source_label, target_label = "Paper", "Person"
    elif rel_type == "APPEARED_AT":
        source_label, target_label = "Paper", "Venue"
    elif rel_type == "STATE_OF_ART":
        source_label, target_label = "Problem", records[0]["target_label"]
    elif rel_type == "RESTS_ON":
        source_label, target_label = "Problem", "Concept"
    elif rel_type == "IN_MODEL":
        source_label, target_label = "Bound", "ComputationModel"
    elif rel_type == "HAS_GAP":
        source_label, target_label = "Problem", "Gap"
    elif rel_type == "HAS_RESEARCH":
        source_label, target_label = "Problem", "ResearchDirection"
    elif rel_type == "FROM_SOURCE":
        source_label, target_label = "Problem", "DataSource"
    elif rel_type == "CLASSIFIED_AS":
        source_label, target_label = records[0]["source_label"], "TaxonomyTerm"
    elif rel_type == "ACTIVE_ON":
        source_label, target_label = records[0]["source_label"], "Problem"
    elif rel_type == "AFFILIATED_WITH":
        source_label, target_label = "Person", "Institution"
    elif rel_type == "GENERALIZES":
        source_label, target_label = "Concept", "Concept"
    elif rel_type == "RELATED_TO":
        source_label, target_label = "Problem", "Problem"
    else:
        raise ValueError(f"Unsupported relationship type: {rel_type}")

    for batch in chunks(records, batch_size):
        rows = "[" + ", ".join(cypher_map(
            {k: v for k, v in row.items() if k not in {"target_label", "source_label"}}
        ) for row in batch) + "]"
        source_id = {
            "AUTHORED_BY": "paper_id", "APPEARED_AT": "paper_id",
            "IN_MODEL": "bound_id", "CLASSIFIED_AS": "source_node_id",
            "ACTIVE_ON": "source_node_id", "AFFILIATED_WITH": "person_id",
            "GENERALIZES": "source_node_id", "RELATED_TO": "source_node_id",
        }.get(rel_type, "problem_id")
        query = (f"UNWIND {rows} AS row "
                 f"MATCH (a:{source_label} {{id: row.{source_id}}}) "
                 f"MATCH (b:{target_label} {{id: row.target_id}}) "
                 f"MERGE (a)-[r:{rel_type}]->(b) "
                 "SET r += row")
        client.query(query)


def validate_paper_resume_ids(client, papers):
    """Read-only guard: planned canonical IDs must already exist under the same identity."""
    result = client.query_readonly(
        "MATCH (p:Paper) RETURN p.id AS id, p.citation_text AS citation_text"
    )
    existing = {row[0]: row[1] for row in result.records if row and row[0]}
    if not existing:
        return 0
    existing_identity = {
        node_id: paper_identity(parse_citation(citation_text or ""))
        for node_id, citation_text in existing.items()
    }
    plan_identity = {
        paper["id"]: paper_identity(paper)
        for paper in papers
    }
    for paper_id, identity in plan_identity.items():
        if paper_id not in existing:
            raise RuntimeError(f"Paper id {paper_id} is absent from non-empty graph; refusing resume")
        if existing_identity[paper_id] != identity:
            raise RuntimeError(f"Paper id {paper_id} resolves to a different citation identity")
    identity_counts = {}
    for identity in existing_identity.values():
        identity_counts[identity] = identity_counts.get(identity, 0) + 1
    existing_aliases = sum(count - 1 for count in identity_counts.values() if count > 1)
    return existing_aliases


def main():
    from etl.loader import prepare

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path("build/source_catalog.json"))
    parser.add_argument("--url", default="http://localhost:8094")
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--load", action="store_true",
                        help="Actually write to Samyama. Without this flag, only validate and plan.")
    args = parser.parse_args()

    if args.batch_size < 1 or args.batch_size > 100:
        parser.error("--batch-size must be between 1 and 100")
    if args.load and urlsplit(args.url).port in {8092, 8093}:
        parser.error("live writes to protected ports 8092 and 8093 are prohibited")

    if not args.catalog.is_file():
        print(f"Catalog not found: {args.catalog}", file=sys.stderr)
        return 1

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    source = catalog.get("source", {})
    if source.get("actual_commit") != PINNED_COMMIT:
        print("Refusing to load: catalog is not from the pinned commit.")
        print("Expected:", PINNED_COMMIT)
        print("Found:", source.get("actual_commit"))
        return 1

    counts = catalog.get("counts", {})
    if counts.get("problem_pages") != 1053 or counts.get("topics") != 35:
        print("Refusing to load: catalog counts do not match the expected source.")
        print(json.dumps(counts, indent=2))
        return 1

    data = prepare(catalog)
    from etl.conformance import validate as validate_conformance
    errors = validate_conformance(data, raise_on_error=False)
    if errors:
        print(f"Refusing to load: {len(errors)} schema-conformance error(s).")
        for error in errors[:80]:
            print("ERROR:", error)
        return 1
    print("Schema conformance: PASS")
    print_plan(data)

    if not args.load:
        print("\nDRY RUN ONLY. No database writes performed.")
        print("Any later live write requires approval and a verified isolated target (default port 8094).")
        return 0

    client = SamyamaClient.connect(args.url)
    print("\nServer:", client.status())
    if client.ping() != "PONG":
        print("Refusing to load: server ping failed.")
        return 1

    # Check UNWIND/map syntax before starting the write phase.
    test = client.query_readonly(
        "UNWIND [{id: 'parser_preflight'}] AS row RETURN row.id AS id"
    )
    if not test.records:
        print("Cypher preflight returned no result; refusing to load.")
        return 1
    try:
        aliases = validate_paper_resume_ids(client, data["Paper"])
    except RuntimeError as exc:
        print(f"Refusing to resume: {exc}")
        return 1
    if aliases:
        print(f"Existing alternate Paper nodes for canonical works: {aliases}; retained without deletion.")

    print("\nCreating nodes...")
    from etl.conformance import load_spec
    labels = tuple(load_spec()["labels"])
    for label in labels:
        print(f"  {label}: {len(data[label]):,}")
        create_nodes(client, label, data[label], args.batch_size)

    print("\nCreating relationships...")
    relationships = tuple(load_spec()["relationships"])
    for rel_type in relationships:
        print(f"  {rel_type}: {len(data[rel_type]):,}")
        create_relationships(client, rel_type, data[rel_type], args.batch_size)

    final_status = client.status()
    print("\n=== Final server status ===")
    print(final_status)
    print("Planned node records:", sum(
        len(data[label]) for label in
        labels
    ))
    print("Planned relationship records:", sum(
        len(data[rel]) for rel in
        relationships
    ))

    print("PASS: load batches completed. MERGE makes repeated runs idempotent by node id and edge endpoints.")
    return 0
