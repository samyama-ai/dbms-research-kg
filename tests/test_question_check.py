"""All 48 scope questions, answered on the catalog-built graph and checked against the raw pages."""
from __future__ import annotations

import json

import pytest

from benchmarks.reference import CATALOG, DATA, check_all

pytestmark = pytest.mark.skipif(not (CATALOG.is_file() and (DATA / "topics").is_dir()),
                                reason="needs build/source_catalog.json and data/dbms_research")


@pytest.fixture(scope="module")
def results():
    from etl.loader import prepare
    return check_all(prepare(json.loads(CATALOG.read_text(encoding="utf-8"))))


def test_every_question_is_checked_once(results):
    assert [r["question"] for r in results] == list(range(1, 49))


def test_no_answer_is_wrong(results):
    assert [r for r in results if r["verdict"] == "WRONG"] == []


def test_the_three_out_of_scope_questions_are_refused(results):
    assert {r["question"] for r in results if r["verdict"] == "refused"} == {46, 47, 48}


@pytest.mark.parametrize("question", [1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 14, 15, 16, 17, 31, 32, 43])
def test_raw_page_questions_are_exactly_correct(results, question):
    assert results[question - 1]["verdict"] == "correct"
