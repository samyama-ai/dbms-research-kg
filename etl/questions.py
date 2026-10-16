"""Executable answer/refusal contract for all 48 questions in docs/scope.md."""
from __future__ import annotations

from collections import Counter, defaultdict
import re

REFUSALS = {
    46: "The pinned catalog contains only references from its own problem pages, not global citation counts.",
    47: "The graph is a snapshot pinned to 2026-09 and cannot establish later status.",
    48: "The pinned catalog contains no funding data.",
}
PARTIAL = {
    9: "Citation roles and metadata are parsed from source text and are not independently verified.",
    12: "The source lists current-research prose; named-person extraction is incomplete.",
    13: "Only source-explicit, allow-listed lab/group names can be returned; affiliation is not inferred.",
    18: "Survey role is stored on each problem-paper citation; counts cover this catalog only.",
    19: "Only years explicitly parsed from citation text are available.",
    21: "Identifiers are extracted from the pinned citation text; no DBLP lookup is performed.",
    27: "Institution extraction is limited to source-explicit recognized names.",
    28: "Without external identity resolution, variants may remain split or homonyms merged.",
    29: "Only explicitly allow-listed algorithm names are extracted from SOTA text.",
    30: "System extraction is limited to source-explicit allow-listed names.",
    34: "Closed status follows the stated/keyword §6 verdict; prose bounds are not compared mechanically.",
    35: "Only computed relationships present in the graph can be returned.",
    36: "Topic connectivity is computed from represented related-problem links only.",
    37: "Concept extraction uses a fixed source-phrase list and is incomplete.",
    38: "Only explicitly represented concept hierarchy links are returned.",
    39: "Vector search is not available in this loader harness; no similarity ranking is fabricated.",
    40: "Bridge ranking is limited to represented problem relations and topics.",
    41: "Gap width is prose and cannot be measured; open/unstated gaps can be listed only.",
    42: "Researcher activity extraction is incomplete; an empty result does not prove no researcher exists.",
    45: "Only parsed integer citation years are counted; unparsed citations remain unknown.",
}

QUESTION_IDS = tuple(range(1, 49))


def question_policy(question_id: int) -> str:
    if question_id in REFUSALS:
        return "refuse"
    if question_id in PARTIAL or question_id in {13, 34, 41}:
        return "partial"
    return "answer"


def _index(data, label):
    return {node.get("id"): node for node in data.get(label, [])}


def _problem(data, problem_id):
    problems = _index(data, "Problem")
    return problems.get(problem_id) or problems.get("problem:" + str(problem_id))


def _rows(data, rel, problem_id):
    return [r for r in data.get(rel, []) if r.get("problem_id") == problem_id]


def _count_by(rows, key):
    return dict(Counter(r.get(key) for r in rows if r.get(key) is not None))


def answer_question(question_id: int, data: dict, params: dict | None = None) -> dict:
    """Answer from prepared graph records, marking bounded answers and refusals."""
    if question_id not in QUESTION_IDS:
        raise ValueError(f"Unknown question number: {question_id}")
    params = params or {}
    if question_id in REFUSALS:
        return {"question_id": question_id, "status": "refusal", "data": [],
                "reason": REFUSALS[question_id]}
    problems = data.get("Problem", [])
    papers = data.get("Paper", [])
    people = data.get("Person", [])
    paper_by_id = _index(data, "Paper")
    person_by_id = _index(data, "Person")
    concept_by_id = _index(data, "Concept")
    problem_id = params.get("problem_id")
    p = _problem(data, problem_id) if problem_id else None
    result = []

    if question_id == 1:
        result = data.get("Topic", [])
    elif question_id == 2:
        result = {"total": len(problems), "open": sum(x.get("status") == "open" for x in problems)}
    elif question_id == 3:
        totals = Counter(x.get("topic_id") for x in problems)
        result = [{"topic_id": k, "problem_count": v} for k, v in sorted(totals.items())]
    elif question_id == 4:
        opens = Counter(x.get("topic_id") for x in problems if x.get("status") == "open")
        result = [{"topic_id": k, "open_count": v} for k, v in opens.most_common()]
    elif question_id == 5:
        result = [x for x in problems if x.get("status") == "solved-but-impractical"]
    elif question_id == 6:
        cutoff = params.get("before", "9999-99")
        result = [x for x in problems if (x.get("last_reviewed") or "") < cutoff
                  or not x.get("last_substantive_update")]
    elif question_id == 7:
        result = ({k: p.get(k) for k in ("id", "title", "status", "problem_statement")} if p else [])
    elif question_id == 8:
        result = next((t for t in data.get("Topic", []) if p and t.get("id") == p.get("topic_id")), [])
    elif question_id in {9, 18, 22}:
        edges = data.get("CITES", [])
        if p:
            edges = _rows(data, "CITES", p["id"])
        if question_id == 18:
            edges = [e for e in edges if e.get("role") == "survey"]
        if question_id == 22:
            edges = [e for e in edges if e.get("verification_status") == "unverified"]
        result = [{**e, "paper": paper_by_id.get(e.get("target_id"), {})} for e in edges]
    elif question_id == 10:
        result = {direction: [b for b in data.get("Bound", []) if p and b.get("problem_id") == p["id"] and b.get("direction") == direction]
                  for direction in ("upper", "lower")}
        result["models"] = [e for e in data.get("IN_MODEL", []) if any(b.get("id") == e.get("bound_id") for side in result.values() if isinstance(side, list) for b in side)]
    elif question_id == 11:
        result = next((g for g in data.get("Gap", []) if p and g.get("problem_id") == p["id"]), [])
    elif question_id in {12, 13}:
        labels = {"Person"} if question_id == 12 else {"Institution"}
        edge_rows = _rows(data, "ACTIVE_ON", p["id"]) if p else data.get("ACTIVE_ON", [])
        result = [e for e in edge_rows if e.get("source_label") in labels]
    elif question_id == 14:
        result = p.get("worked_example", "") if p else []
    elif question_id == 15:
        result = [x for x in data.get("FutureDirection", []) if p and x.get("problem_id") == p["id"]]
    elif question_id in {16, 17}:
        citations = data.get("CITES", [])
        by_paper = defaultdict(set)
        for edge in citations:
            problem = _problem(data, edge.get("problem_id"))
            if problem:
                by_paper[edge.get("target_id")].add(problem.get("topic_id") if question_id == 17 else problem.get("id"))
        result = [{"paper": paper_by_id.get(k, {}), "problem_count": len(v) if question_id == 16 else len({x for x in v if x}), "topics": sorted(v) if question_id == 17 else []}
                  for k, v in sorted(by_paper.items(), key=lambda kv: -len(kv[1]))]
    elif question_id == 19:
        year = int(params.get("after_year", 0))
        result = [x for x in papers if isinstance(x.get("year"), int) and x["year"] > year]
    elif question_id == 20:
        counts = Counter(e.get("target_id") for e in data.get("APPEARED_AT", []))
        result = [{"venue": _index(data, "Venue").get(k, {}), "paper_count": v} for k, v in counts.most_common()]
    elif question_id == 21:
        result = [{"id": x.get("id"), "doi": x.get("doi"), "arxiv_id": x.get("arxiv_id"), "dblp_key": x.get("dblp_key")}
                  for x in papers if x.get("doi") or x.get("arxiv_id") or x.get("dblp_key")]
    elif question_id == 23:
        counts = Counter(e.get("target_id") for e in data.get("AUTHORED_BY", []))
        result = [{"person": person_by_id.get(k, {}), "cited_papers": v} for k, v in counts.most_common()]
    elif question_id == 24:
        counts = Counter(e.get("target_id") for e in data.get("ACTIVE_ON", []))
        result = [{"person": person_by_id.get(k, {}), "active_problems": v} for k, v in counts.most_common()]
    elif question_id == 25:
        person_id = params.get("person_id")
        authored = {e.get("paper_id") for e in data.get("AUTHORED_BY", []) if e.get("target_id") == person_id}
        coauthors = Counter(e.get("target_id") for e in data.get("AUTHORED_BY", []) if e.get("paper_id") in authored and e.get("target_id") != person_id)
        result = [{"person": person_by_id.get(k, {}), "shared_papers": v} for k, v in coauthors.most_common()]
    elif question_id == 26:
        result = [x for x in people if x.get("dblp_pid") or x.get("orcid")]
    elif question_id == 27:
        counts = Counter(e.get("target_id") for e in data.get("ACTIVE_ON", [])
                         if _problem(data, e.get("problem_id")) and _problem(data, e.get("problem_id")).get("status") == "open")
        result = [{"institution": _index(data, "Institution").get(k, {}), "active_open_problems": v} for k, v in counts.most_common()]
    elif question_id == 28:
        by_name = defaultdict(list)
        for person in people:
            by_name[re.sub(r"[^\w]", "", person.get("name", "").casefold())].append(person)
        result = [group for group in by_name.values() if len(group) > 1]
    elif question_id in {29, 30, 31}:
        label = "Algorithm" if question_id == 29 else "System"
        edges = [e for e in data.get("STATE_OF_ART", []) if e.get("target_label") == label]
        if p:
            edges = [e for e in edges if e.get("problem_id") == p["id"]]
        result = [{"entity": _index(data, label).get(e.get("target_id"), {}), "edge": e} for e in edges]
    elif question_id == 32:
        result = [b for b in data.get("Bound", []) if b.get("direction") == "lower" and re.search(r"\b(SETH|ETH|3SUM|OV|fine[- ]grained)\b", b.get("text", ""), re.I)]
    elif question_id == 33:
        result = {kind: [b for b in data.get("Bound", []) if b.get("kind") == kind] for kind in ("time", "space", "impossibility")}
    elif question_id == 34:
        result = [g for g in data.get("Gap", []) if g.get("verdict") == "closed"]
    elif question_id == 35:
        result = [e for e in data.get("RELATED_TO", []) if p and p["id"] in {e.get("problem_id"), e.get("target_id")}]
    elif question_id == 36:
        result = data.get("RELATED_TO", [])
    elif question_id == 37:
        result = [{"concept": concept_by_id.get(k, {}), "problems": [e.get("problem_id") for e in data.get("RESTS_ON", []) if e.get("target_id") == k]}
                  for k in _index(data, "Concept")]
    elif question_id == 38:
        result = data.get("GENERALIZES", [])
    elif question_id == 39:
        result = []
    elif question_id == 40:
        result = data.get("RELATED_TO", [])
    elif question_id == 41:
        result = [g for g in data.get("Gap", []) if g.get("verdict") in {"open", "unstated"}]
    elif question_id == 42:
        active = {e.get("problem_id") for e in data.get("ACTIVE_ON", [])}
        result = [x for x in problems if x.get("status") == "open" and x.get("id") not in active]
    elif question_id == 43:
        counts = Counter(e.get("problem_id") for e in data.get("CLOSING_REQUIRES", []))
        by_topic = Counter()
        for problem in problems:
            by_topic[problem.get("topic_id")] += counts.get(problem.get("id"), 0)
        result = [{"topic_id": k, "future_work_count": v} for k, v in by_topic.most_common()]
    elif question_id == 44:
        groups = defaultdict(list)
        for item in data.get("FutureDirection", []):
            key = " ".join(item.get("text", "").casefold().split())
            groups[key].append(item)
        result = [items for items in groups.values() if len({x.get("problem_id") for x in items}) > 1]
    elif question_id == 45:
        cutoff = int(params.get("before_year", 2015))
        paper_ids = {x.get("id") for x in papers if isinstance(x.get("year"), int) and x["year"] > 0}
        recent = {x.get("id") for x in papers if isinstance(x.get("year"), int) and x["year"] > cutoff}
        cites = defaultdict(set)
        for edge in data.get("CITES", []):
            cites[edge.get("problem_id")].add(edge.get("target_id"))
        result = [x for x in problems if x.get("status") == "open" and cites[x.get("id")] and not (cites[x.get("id")] & recent)]
    policy = question_policy(question_id)
    return {"question_id": question_id, "status": policy, "data": result,
            "reason": PARTIAL.get(question_id, "")}
