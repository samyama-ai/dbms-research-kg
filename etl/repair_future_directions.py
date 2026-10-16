"""Safely identify and optionally remove index-shift FutureDirection duplicates.

Default mode is read-only. Deletion requires the explicit --apply flag.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

from samyama import SamyamaClient

from etl.loader import PINNED_COMMIT, cypher_string, stable_id


def expected_future_ids(catalog):
    """Map source identity to the old canonical (index 0) and bad (index 1) IDs."""
    expected = {}
    for problem in catalog["problems"]:
        for index, text in enumerate(problem["future_work_items"]):
            text = text.strip()
            if not text:
                continue
            identity = (problem["id"], text)
            if identity in expected:
                raise ValueError(f"Pinned source repeats a future-work item in {problem['id']}")
            source_path = problem["source_path"]
            expected[identity] = {
                "canonical_id": stable_id("future", f"{problem['id']}\n{index}\n{text}"),
                "shifted_id": stable_id("future", f"{problem['id']}\n{index + 1}\n{text}"),
                "source_path": source_path,
                "text": text,
            }
    return expected


def audit_nodes(rows, expected):
    """Return shifted duplicate IDs after proving each row matches pinned source."""
    by_id = {row[0]: row for row in rows}
    if len(by_id) != len(rows):
        raise ValueError("FutureDirection node IDs are not unique")
    duplicate_ids = []
    found_canonical = set()
    for row in rows:
        node_id, problem_id, text, source_path = row
        identity = (problem_id, text)
        source = expected.get(identity)
        if source is None or source_path != source["source_path"]:
            raise ValueError(f"Node {node_id} does not match a pinned source item")
        if node_id == source["canonical_id"]:
            found_canonical.add(identity)
        elif node_id == source["shifted_id"]:
            duplicate_ids.append(node_id)
        else:
            raise ValueError(f"Node {node_id} has an unrecognized ID for its source item")
    missing = set(expected) - found_canonical
    if missing:
        raise ValueError(f"Canonical zero-based nodes are missing for {len(missing)} source items")
    return duplicate_ids


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path("build/source_catalog.json"))
    parser.add_argument("--url", default="http://localhost:8093")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--apply", action="store_true",
                        help="Delete only verified shifted duplicates with no relationships")
    args = parser.parse_args()
    if urlsplit(args.url).port == 8092:
        parser.error("port 8092 is the read-only reference graph and is prohibited")
    if args.batch_size < 1 or args.batch_size > 500:
        parser.error("--batch-size must be between 1 and 500")
    if not args.catalog.is_file():
        print(f"Catalog not found: {args.catalog}", file=sys.stderr)
        return 1

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    if catalog.get("source", {}).get("actual_commit") != PINNED_COMMIT:
        print("Refusing repair: catalog is not from the pinned commit.")
        return 1

    client = SamyamaClient.connect(args.url)
    print("Server:", client.status())
    expected = expected_future_ids(catalog)
    rows = client.query_readonly(
        "MATCH (n:FutureDirection) "
        "RETURN n.id AS id, n.problem_id AS problem_id, n.text AS text, "
        "n.source_path AS source_path"
    ).records
    try:
        duplicate_ids = audit_nodes(rows, expected)
    except ValueError as exc:
        print(f"Refusing repair: {exc}")
        return 1

    duplicate_set = set(duplicate_ids)
    incident = client.query_readonly(
        "MATCH (n:FutureDirection)-[r]-(other) "
        "RETURN n.id AS id, type(r) AS type, other.id AS other_id"
    ).records
    attached_duplicates = [row for row in incident if row[0] in duplicate_set]
    if attached_duplicates:
        print(f"Refusing repair: {len(attached_duplicates)} candidate duplicate nodes have relationships.")
        for row in attached_duplicates[:20]:
            print("INCIDENT:", row)
        return 1

    print(f"Verified source items: {len(expected):,}")
    print(f"Canonical nodes retained: {len(expected):,}")
    print(f"Shifted duplicate nodes eligible for deletion: {len(duplicate_ids):,}")
    print("Relationships attached to deletion candidates: 0")
    if not args.apply:
        print("DRY RUN ONLY. No database writes performed. Add --apply only after approval.")
        return 0

    for start in range(0, len(duplicate_ids), args.batch_size):
        batch = duplicate_ids[start:start + args.batch_size]
        values = "[" + ", ".join(cypher_string(value) for value in batch) + "]"
        client.query(
            f"UNWIND {values} AS id MATCH (n:FutureDirection {{id: id}}) DELETE n"
        )

    final_rows = client.query_readonly(
        "MATCH (n:FutureDirection) RETURN n.id AS id, n.problem_id AS problem_id, "
        "n.text AS text, n.source_path AS source_path"
    ).records
    try:
        remaining_duplicates = audit_nodes(final_rows, expected)
    except ValueError as exc:
        print(f"ERROR after repair: {exc}")
        return 1
    if remaining_duplicates:
        print(f"ERROR after repair: {len(remaining_duplicates)} shifted duplicate nodes remain")
        return 1
    print("PASS: one canonical FutureDirection node remains per source item.")
    print("Final status:", client.status())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
