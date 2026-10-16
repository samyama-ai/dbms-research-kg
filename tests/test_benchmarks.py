"""The benchmark file covers every scope question that Cypher can answer."""
from __future__ import annotations

from benchmarks.run import MUST_BE_EMPTY, parse, summary


def test_every_scope_question_but_vector_search_has_cypher():
    numbers = [b["n"] for b in parse()]
    assert numbers == [n for n in range(1, 49) if n != 39]
    assert all(b["cypher"].upper().startswith("MATCH") for b in parse())


def test_refusal_questions_are_marked():
    assert MUST_BE_EMPTY == {26, 44, 46, 47, 48}


def test_summary_reports_no_rows_and_truncates():
    assert summary(["a"], []) == "no rows"
    assert summary(["a"], [[1], [2], [3], [4]], limit=2) == "a 1 | a 2 (+2 more)"
