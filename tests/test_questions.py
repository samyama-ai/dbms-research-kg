import pytest

from etl.questions import QUESTION_IDS, REFUSALS, answer_question, question_policy


@pytest.fixture
def tiny_graph():
    return {
        "Problem": [{"id": "01-test/p", "title": "P", "status": "open",
                     "topic_id": "01-test", "problem_statement": "S",
                     "worked_example": "Example", "last_reviewed": "2026-01"}],
        "Topic": [{"id": "01-test", "name": "Test"}],
        "Paper": [], "Person": [], "Venue": [], "Institution": [], "Concept": [],
        "Algorithm": [], "System": [], "Bound": [], "ComputationModel": [],
        "Gap": [{"id": "01-test/p#gap", "problem_id": "01-test/p",
                 "text": "Need a proof", "verdict": "open"}],
        "ResearchDirection": [], "FutureDirection": [], "DataSource": [],
        "TaxonomyTerm": [], "IN_TOPIC": [{"problem_id": "01-test/p", "target_id": "01-test"}],
        "CITES": [], "AUTHORED_BY": [], "APPEARED_AT": [], "RESTS_ON": [],
        "GENERALIZES": [], "HAS_BOUND": [], "IN_MODEL": [], "STATE_OF_ART": [],
        "HAS_GAP": [], "HAS_RESEARCH": [], "CLOSING_REQUIRES": [], "ACTIVE_ON": [],
        "AFFILIATED_WITH": [], "RELATED_TO": [], "FROM_SOURCE": [], "CLASSIFIED_AS": [],
    }


@pytest.mark.parametrize("question_id", QUESTION_IDS)
def test_every_scope_question_has_explicit_answer_or_refusal_behavior(question_id, tiny_graph):
    result = answer_question(question_id, tiny_graph)
    assert result["question_id"] == question_id
    assert result["status"] == {"refuse": "refusal"}.get(question_policy(question_id), question_policy(question_id))
    if question_id in REFUSALS:
        assert result["data"] == []
        assert result["reason"]


@pytest.mark.parametrize("question_id", (46, 47, 48))
def test_out_of_scope_questions_refuse_without_data(question_id, tiny_graph):
    result = answer_question(question_id, tiny_graph)
    assert result == {"question_id": question_id, "status": "refusal", "data": [],
                      "reason": REFUSALS[question_id]}


def test_core_aggregate_and_problem_lookup_behaviors(tiny_graph):
    assert answer_question(2, tiny_graph)["data"] == {"total": 1, "open": 1}
    assert answer_question(7, tiny_graph, {"problem_id": "01-test/p"})["data"]["title"] == "P"
    assert answer_question(8, tiny_graph, {"problem_id": "01-test/p"})["data"]["id"] == "01-test"
    assert answer_question(11, tiny_graph, {"problem_id": "01-test/p"})["data"]["verdict"] == "open"
    assert answer_question(14, tiny_graph, {"problem_id": "01-test/p"})["data"] == "Example"
