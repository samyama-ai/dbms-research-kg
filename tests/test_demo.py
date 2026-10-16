"""The narrated demo: ten questions, one refusal, and a Cypher file that matches the story."""
from __future__ import annotations

from demo.demo import BASIS, STORY, write_cypher


def test_ten_questions_each_with_a_known_basis():
    assert len(STORY) == 10
    assert {basis for _, _, basis, _, _ in STORY} <= set(BASIS)


def test_exactly_one_question_must_return_nothing():
    assert [title for title, _, basis, _, _ in STORY if basis == "none"] == [
        "How much funding has each problem received?"]


def test_write_cypher_lists_every_query_in_order(tmp_path):
    text = write_cypher(tmp_path / "queries.cypher").read_text(encoding="utf-8")
    positions = [text.index(statement) for *_, statement in STORY]
    assert positions == sorted(positions)
