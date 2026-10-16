"""Tests for etl/source_parser.py helpers that read the catalog's index files."""
from __future__ import annotations

from etl.source_parser import topic_scopes


def test_topic_scope_is_read_from_the_taxonomy_table(tmp_path):
    (tmp_path / "TAXONOMY.md").write_text(
        "| # | Topic | Directory | Scope |\n"
        "|---|-------|-----------|-------|\n"
        "| 01 | Relational Model | [`01-relational-theory`](./topics/01-relational-theory/) "
        "| Relational algebra/calculus, FDs/MVDs/JDs |\n"
        "| 02 | Query Optimization | [`02-query-optimization`](./topics/02-query-optimization/) |  |\n",
        encoding="utf-8")
    assert topic_scopes(tmp_path) == {"01-relational-theory": "Relational algebra/calculus, FDs/MVDs/JDs"}


def test_no_taxonomy_file_gives_no_scopes(tmp_path):
    assert topic_scopes(tmp_path) == {}
