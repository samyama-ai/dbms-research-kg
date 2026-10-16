"""Executable answer/refusal contract for all 48 questions in benchmarks/scope.md.

`answer_question(n, data, params)` answers question n from prepared graph
records (the output of etl.loader.prepare). Rankings are sorted, most first.
Status is 'answer', 'partial' (the reason says what is missing) or 'refusal'.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict

REFUSALS = {
    46: "The pinned catalog contains only references from its own problem pages, not global citation counts.",
    47: "The graph is a snapshot pinned to 2026-09 and cannot establish later status.",
    48: "The pinned catalog contains no funding data.",
}
PARTIAL = {
    9: "Citation roles and metadata are parsed from source text and are not independently verified.",
    12: "Only people whose authored name form occurs in §7 are linked; other named people are missed.",
    13: "Institutions come from a checked list matched in §7; groups not on the list are missed.",
    18: "Survey role is stored on each problem-paper citation; counts cover this catalog only.",
    19: "Only years explicitly parsed from citation text are available.",
    21: "Identifiers are extracted from the pinned citation text; no DBLP lookup is performed.",
    22: "Only references whose own text says unverified are identified; pages that only give a count are listed.",
    26: "No DBLP or ORCID lookup is performed in v1 (schema.md §8 decision 1), so no profiles are stored.",
    27: "Institutions come from a checked list matched in §7; affiliation is what the page states.",
    28: "Variants are grouped by first initial and surname; without DBLP, homonyms can share a group.",
    29: "Algorithms are bold names in §3 plus a reviewed list; unbolded methods are missed.",
    30: "Systems are bold names in §3 plus a reviewed list; unbolded systems are missed.",
    34: "Closed status follows the stated/keyword §6 verdict; prose bounds are not compared mechanically.",
    37: "Concepts come from a fixed list of 90 matched in §2.",
    38: "The hierarchy is the reviewed project list of concept pairs, not extracted from pages.",
    39: "Vector search is not available in this harness; no similarity ranking is fabricated.",
    41: "Gap width is prose and cannot be measured; problems are listed by verdict, not ranked by width.",
    42: "An empty result for a problem means no linked person, not that nobody works on it.",
    44: "Only future-work items with identical normalised text are matched; paraphrases are missed.",
    45: "Only parsed integer citation years are counted; unparsed citations remain unknown.",
}

QUESTION_IDS = tuple(range(1, 49))


def question_policy(question_id: int) -> str:
    if question_id in REFUSALS:
        return "refuse"
    if question_id in PARTIAL:
        return "partial"
    return "answer"


def _index(data, label):
    return {node.get("id"): node for node in data.get(label, [])}


def _ranked(counter, key_name, lookup=None, value_name="count", limit=None):
    rows = [{key_name: lookup.get(k, {"id": k}) if lookup is not None else k, value_name: v}
            for k, v in sorted(counter.items(), key=lambda kv: (-kv[1], str(kv[0])))]
    return rows[:limit] if limit else rows


def _person_id(data, params):
    if params.get("person_id"):
        return params["person_id"]
    name = (params.get("person_name") or "").casefold()
    return next((p["id"] for p in data.get("Person", []) if p.get("name", "").casefold() == name), None)


def answer_question(question_id: int, data: dict, params: dict | None = None) -> dict:
    """Answer from prepared graph records, marking bounded answers and refusals."""
    if question_id not in QUESTION_IDS:
        raise ValueError(f"Unknown question number: {question_id}")
    params = params or {}
    if question_id in REFUSALS:
        return {"question_id": question_id, "status": "refusal", "data": [],
                "reason": REFUSALS[question_id]}
    problems = data.get("Problem", [])
    problem_by_id = _index(data, "Problem")
    paper_by_id = _index(data, "Paper")
    person_by_id = _index(data, "Person")
    topic_of = {p.get("id"): p.get("topic_id") for p in problems}
    p = problem_by_id.get(params.get("problem_id")) if params.get("problem_id") else None
    pid = p["id"] if p else None
    result = []

    if question_id == 1:
        result = sorted(data.get("Topic", []), key=lambda t: str(t.get("number", t.get("id"))))
    elif question_id == 2:
        result = {"total": len(problems), "open": sum(x.get("status") == "open" for x in problems)}
    elif question_id == 3:
        totals = Counter(x.get("topic_id") for x in problems)
        result = [{"topic_id": k, "problem_count": v} for k, v in sorted(totals.items())]
    elif question_id == 4:
        opens = Counter(x.get("topic_id") for x in problems if x.get("status") == "open")
        result = _ranked(opens, "topic_id", value_name="open_count")
    elif question_id == 5:
        result = [x for x in problems if x.get("status") == "solved-but-impractical"]
    elif question_id == 6:
        cutoff = params.get("before", "9999-99")
        result = [x for x in problems if (x.get("last_reviewed") or "") < cutoff]
    elif question_id == 7:
        result = {k: p.get(k) for k in ("id", "title", "status", "problem_statement")} if p else []
    elif question_id == 8:
        result = next((t for t in data.get("Topic", []) if p and t.get("id") == p.get("topic_id")), [])
    elif question_id == 22:
        marked = [e for e in data.get("CITES", []) if e.get("verification_status") == "unverified"
                  and (not pid or e.get("problem_id") == pid)]
        per_page = Counter(e["problem_id"] for e in marked)
        result = {"citations": [{**e, "paper": paper_by_id.get(e.get("target_id"), {})} for e in marked],
                  "pages_with_unidentified": sorted(
                      x["id"] for x in problems
                      if int(x.get("refs_unverified") or 0) > per_page[x["id"]] and (not pid or x["id"] == pid))}
    elif question_id in {9, 18}:
        edges = [e for e in data.get("CITES", []) if not pid or e.get("problem_id") == pid]
        if question_id == 18:
            surveys = Counter(e.get("target_id") for e in edges if e.get("role") == "survey")
            result = _ranked(surveys, "paper", paper_by_id, "problem_count")
        else:
            result = [{**e, "paper": paper_by_id.get(e.get("target_id"), {})}
                      for e in sorted(edges, key=lambda e: e.get("position", 0))]
    elif question_id == 10:
        bounds = [b for b in data.get("Bound", []) if pid and b.get("problem_id") == pid]
        ids = {b["id"] for b in bounds}
        models = _index(data, "ComputationModel")
        result = {"upper": [b for b in bounds if b.get("direction") == "upper"],
                  "lower": [b for b in bounds if b.get("direction") == "lower"],
                  "models": [{"bound_id": e["bound_id"], "model": models.get(e["target_id"], {}).get("name")}
                             for e in data.get("IN_MODEL", []) if e.get("bound_id") in ids]}
    elif question_id == 11:
        result = next((g for g in data.get("Gap", []) if pid and g.get("problem_id") == pid), [])
    elif question_id in {12, 13}:
        label = "Person" if question_id == 12 else "Institution"
        nodes = person_by_id if label == "Person" else _index(data, "Institution")
        result = [{"who": nodes.get(e.get("source_node_id"), {}).get("name"), "direction": e.get("direction")}
                  for e in data.get("ACTIVE_ON", [])
                  if e.get("source_label") == label and (not pid or e.get("problem_id") == pid)]
    elif question_id == 14:
        result = p.get("worked_example", "") if p else []
    elif question_id == 15:
        result = sorted((x for x in data.get("FutureDirection", []) if pid and x.get("problem_id") == pid),
                        key=lambda x: x.get("id"))
    elif question_id in {16, 17}:
        by_paper = defaultdict(set)
        for edge in data.get("CITES", []):
            value = topic_of.get(edge.get("problem_id")) if question_id == 17 else edge.get("problem_id")
            by_paper[edge.get("target_id")].add(value)
        name = "problem_count" if question_id == 16 else "topic_count"
        result = _ranked(Counter({k: len(v) for k, v in by_paper.items()}), "paper", paper_by_id, name)
    elif question_id == 19:
        year = int(params.get("after_year", 0))
        dated = [x for x in data.get("Paper", []) if isinstance(x.get("year"), int)]
        result = {"after_year": year, "count": sum(x["year"] > year for x in dated),
                  "by_decade": dict(sorted(Counter(x["year"] // 10 * 10 for x in dated).items()))}
    elif question_id == 20:
        counts = Counter(e.get("target_id") for e in data.get("APPEARED_AT", []))
        result = _ranked(counts, "venue", _index(data, "Venue"), "paper_count")
    elif question_id == 21:
        papers = data.get("Paper", [])
        result = {"doi": sum(bool(x.get("doi")) for x in papers), "arxiv": sum(bool(x.get("arxiv_id")) for x in papers),
                  "dblp_only": sum(bool(x.get("dblp_key")) and not x.get("doi") and not x.get("arxiv_id")
                                   for x in papers),
                  "none": sum(not (x.get("doi") or x.get("arxiv_id") or x.get("dblp_key")) for x in papers),
                  "total": len(papers)}
    elif question_id == 23:
        counts = Counter(e.get("target_id") for e in data.get("AUTHORED_BY", []))
        result = _ranked(counts, "person", person_by_id, "papers")
    elif question_id == 24:
        problems_of, topics_of = defaultdict(set), defaultdict(set)
        for e in data.get("ACTIVE_ON", []):
            if e.get("source_label") == "Person":
                problems_of[e["source_node_id"]].add(e.get("problem_id"))
                topics_of[e["source_node_id"]].add(topic_of.get(e.get("problem_id")))
        result = [{"person": person_by_id.get(k, {}), "problems": len(v), "topics": len(topics_of[k])}
                  for k, v in sorted(problems_of.items(), key=lambda kv: (-len(kv[1]), kv[0]))]
    elif question_id == 25:
        person_id = _person_id(data, params)
        authored = {e.get("paper_id") for e in data.get("AUTHORED_BY", []) if e.get("target_id") == person_id}
        coauthors = Counter(e.get("target_id") for e in data.get("AUTHORED_BY", [])
                            if e.get("paper_id") in authored and e.get("target_id") != person_id)
        result = _ranked(coauthors, "person", person_by_id, "shared_papers")
    elif question_id == 26:
        result = [x for x in data.get("Person", []) if x.get("dblp_pid") or x.get("orcid")]
    elif question_id == 27:
        counts = Counter(e.get("source_node_id") for e in data.get("ACTIVE_ON", [])
                         if e.get("source_label") == "Institution"
                         and problem_by_id.get(e.get("problem_id"), {}).get("status") == "open")
        result = _ranked(counts, "institution", _index(data, "Institution"), "open_problems")
    elif question_id == 28:
        groups = defaultdict(set)
        for person in data.get("Person", []):
            name = person.get("name", "")
            if "," in name:                       # "Neumann, T." -> "T. Neumann"
                surname, _, given = name.partition(",")
                name = f"{given} {surname}"
            tokens = re.findall(r"[^\W\d_]+", name)
            if len(tokens) >= 2:
                groups[(tokens[0][0].casefold(), tokens[-1].casefold())].add(person.get("name"))
        result = [sorted(names) for _, names in sorted(groups.items()) if len(names) > 1]
    elif question_id in {29, 30}:
        label = "Algorithm" if question_id == 29 else "System"
        counts = Counter(e.get("target_id") for e in data.get("STATE_OF_ART", []) if e.get("target_label") == label)
        result = _ranked(counts, label.casefold(), _index(data, label), "problems")
    elif question_id == 31:
        names = {**_index(data, "Algorithm"), **_index(data, "System")}
        result = {kind: sorted(names.get(e["target_id"], {}).get("name", "") for e in data.get("STATE_OF_ART", [])
                               if e.get("problem_id") == pid and e.get("kind") == kind)
                  for kind in ("theory", "systems")}
    elif question_id == 32:
        models = {m["id"]: m for m in data.get("ComputationModel", [])}
        lower = {b["id"]: b for b in data.get("Bound", []) if b.get("direction") == "lower"}
        hits = {lower[e["bound_id"]]["problem_id"] for e in data.get("IN_MODEL", [])
                if e.get("bound_id") in lower and models.get(e.get("target_id"), {}).get("class") == "fine-grained"}
        result = sorted(hits)
    elif question_id == 33:
        result = dict(Counter(b.get("kind") for b in data.get("Bound", [])).most_common())
    elif question_id == 34:
        result = [g for g in data.get("Gap", []) if g.get("verdict") == "closed"]
    elif question_id == 35:
        result = sorted(({"problem": e["target_id"] if e.get("problem_id") == pid else e.get("problem_id"),
                          "score": e.get("score")} for e in data.get("RELATED_TO", [])
                         if pid in {e.get("problem_id"), e.get("target_id")}), key=lambda r: -r["score"])
    elif question_id in {36, 40}:
        pairs, bridges = Counter(), defaultdict(set)
        for e in data.get("RELATED_TO", []):
            a, b = topic_of.get(e.get("problem_id")), topic_of.get(e.get("target_id"))
            if a and b and a != b:
                pairs[tuple(sorted((a, b)))] += 1
                bridges[e["problem_id"]].add(b)
                bridges[e["target_id"]].add(a)
        if question_id == 36:
            result = [{"topics": list(k), "links": v} for k, v in pairs.most_common()]
        else:
            result = [{"problem": k, "other_topics": len(v)}
                      for k, v in sorted(bridges.items(), key=lambda kv: (-len(kv[1]), kv[0]))]
    elif question_id == 37:
        concept_ids = {c["id"] for c in data.get("Concept", [])
                       if not params.get("concept") or c.get("name") == params["concept"]}
        by_concept = Counter(e["target_id"] for e in data.get("RESTS_ON", []) if e.get("target_id") in concept_ids)
        result = _ranked(by_concept, "concept", _index(data, "Concept"), "problems")
    elif question_id == 38:
        names = {c["id"]: c.get("name") for c in data.get("Concept", [])}
        result = [{"broader": names.get(e.get("source_node_id")), "narrower": names.get(e.get("target_id"))}
                  for e in data.get("GENERALIZES", [])]
    elif question_id == 39:
        result = []
    elif question_id == 41:
        result = [g for g in data.get("Gap", []) if g.get("verdict") == "open"
                  and problem_by_id.get(g.get("problem_id"), {}).get("status") == "open"]
    elif question_id == 42:
        active = {e.get("problem_id") for e in data.get("ACTIVE_ON", []) if e.get("source_label") == "Person"}
        result = [x for x in problems if x.get("status") == "open" and x.get("id") not in active]
    elif question_id == 43:
        counts = Counter(topic_of.get(e.get("problem_id")) for e in data.get("CLOSING_REQUIRES", []))
        result = _ranked(counts, "topic_id", value_name="future_work_count")
    elif question_id == 44:
        groups = defaultdict(list)
        for item in data.get("FutureDirection", []):
            groups[" ".join(re.findall(r"\w+", item.get("text", "").casefold()))].append(item)
        result = [items for items in groups.values() if len({x.get("problem_id") for x in items}) > 1]
    elif question_id == 45:
        cutoff = int(params.get("before_year", 2015))
        recent = {x.get("id") for x in data.get("Paper", []) if isinstance(x.get("year"), int) and x["year"] > cutoff}
        cites = defaultdict(set)
        for edge in data.get("CITES", []):
            cites[edge.get("problem_id")].add(edge.get("target_id"))
        result = [x for x in problems if x.get("status") == "open" and cites[x.get("id")]
                  and not (cites[x.get("id")] & recent)]
    return {"question_id": question_id, "status": question_policy(question_id), "data": result,
            "reason": PARTIAL.get(question_id, "")}
