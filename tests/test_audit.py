"""The audit must pass on the built v5 graph and fail when a copy is broken."""
from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from etl.audit import run

GRAPH = Path(__file__).resolve().parents[1] / "build" / "dbms_research_kg.schema-candidate-v5.sqlite"
pytestmark = pytest.mark.skipif(not GRAPH.is_file(), reason="v5 candidate is not built")


def status(results, part, item_prefix):
    return next(i["status"] for i in results[part] if i["item"].startswith(item_prefix))


def broken_copy(tmp_path, label_or_rel, table, mutate, where=""):
    copy = tmp_path / "graph.sqlite"
    shutil.copy(GRAPH, copy)
    conn = sqlite3.connect(copy)
    col, key = ("label", "node_id") if table == "nodes" else ("rel_type", "edge_id")
    row_id, props = conn.execute(
        f"SELECT {key},properties_json FROM {table} WHERE {col}=? {where} LIMIT 1", (label_or_rel,)).fetchone()
    record = json.loads(props)
    if mutate(record) == "delete":
        conn.execute(f"DELETE FROM {table} WHERE {key}=?", (row_id,))
    else:
        conn.execute(f"UPDATE {table} SET properties_json=? WHERE {key}=?", (json.dumps(record), row_id))
    conn.commit()
    conn.close()
    return copy


def test_v5_passes_every_audited_item():
    results = run(GRAPH, ["taxonomies"])
    assert [len(results[p]) for p in results] == [4]
    assert all(i["status"] == "PASS" for items in results.values() for i in items)


def test_a_missing_classification_fails_the_taxonomy(tmp_path):
    copy = broken_copy(tmp_path, "CLASSIFIED_AS", "edges", lambda r: "delete")
    results = run(copy, ["taxonomies"])
    assert "FAIL" in {i["status"] for i in results["taxonomies"]}
