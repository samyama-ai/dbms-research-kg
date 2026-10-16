"""The audit must pass on the built v5 graph and fail when a copy is broken."""
from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from etl.audit import run

GRAPH = Path(__file__).resolve().parents[1] / "build" / "dbms_research_kg.schema-candidate-v6.sqlite"
pytestmark = pytest.mark.skipif(not GRAPH.is_file(), reason="v6 candidate is not built")


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


def test_v6_passes_every_audited_item():
    results = run(GRAPH, ["taxonomies", "code-lists", "standards"])
    assert [len(results[p]) for p in results] == [4, 12, 6]
    assert all(i["status"] == "PASS" for items in results.values() for i in items)


def test_a_missing_classification_fails_the_taxonomy(tmp_path):
    copy = broken_copy(tmp_path, "CLASSIFIED_AS", "edges", lambda r: "delete")
    results = run(copy, ["taxonomies"])
    assert "FAIL" in {i["status"] for i in results["taxonomies"]}


def test_a_value_outside_the_code_list_fails(tmp_path):
    copy = broken_copy(tmp_path, "Problem", "nodes", lambda r: r.update(status="bogus"))
    assert status(run(copy, ["code-lists"]), "code-lists", "1.") == "FAIL"


def test_an_invented_doi_fails_iso_26324(tmp_path):
    copy = broken_copy(tmp_path, "Paper", "nodes", lambda r: r.update(doi="10.9999/not-in-the-text"),
                       where="AND json_extract(properties_json,'$.doi') IS NOT NULL")
    assert status(run(copy, ["standards"]), "standards", "ISO 26324") == "FAIL"


def test_a_partial_date_fails_iso_8601(tmp_path):
    copy = broken_copy(tmp_path, "Venue", "nodes", lambda r: r.update(retrieved_at="2026-10"))
    assert status(run(copy, ["standards"]), "standards", "ISO 8601") == "FAIL"


def test_a_missing_provenance_field_fails_prov_o(tmp_path):
    copy = broken_copy(tmp_path, "Concept", "nodes", lambda r: r.pop("source_url"))
    assert status(run(copy, ["standards"]), "standards", "PROV-O") == "FAIL"
