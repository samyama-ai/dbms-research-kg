"""Check the answers to all 48 scope questions against the raw catalog pages.

    python -m etl.question_check [--report docs/question-report.md]

Each answer from etl/questions.py, computed on the prepared graph, is compared
with a value re-derived from the raw Markdown in data/dbms_research using simple
regexes, not the graph parser. Where no independent value exists (computed
links), the check is an internal consistency check and says so. Verdicts:

    correct     the answer equals the value read from the raw pages
    consistent  the answer agrees with the graph's own evidence
    limited     a documented partial answer, and the limit holds
    refused     a question the graph must refuse, and it does
    WRONG       anything else
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from etl.questions import QUESTION_IDS, answer_question
from etl.source_entities import CONCEPT_HIERARCHY, CONCEPTS, INSTITUTIONS

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "dbms_research"
CATALOG = ROOT / "build" / "source_catalog.json"
SAMPLE = "01-relational-theory/acyclic-join-dependencies"
PERSON = "T. Neumann"
CONCEPT = "AGM bound"
INSTITUTION = "cmu"


class RawPage:
    """One problem page read with plain regexes."""

    def __init__(self, path: Path):
        text = path.read_text(encoding="utf-8")
        self.id = f"{path.parent.name}/{path.stem}"
        self.topic = path.parent.name
        front = text.split("---", 2)[1] if text.startswith("---") else ""
        self.meta = dict(re.findall(r"^(\w+):\s*\"?([^\"\n#]*?)\"?\s*(?:#.*)?$", front, re.MULTILINE))
        self.sections = {}
        for match in re.finditer(r"^## (\d+)\.[^\n]*\n(.*?)(?=^## \d+\.|^---\s*$|\Z)", text, re.MULTILINE | re.DOTALL):
            self.sections[int(match.group(1))] = match.group(2).strip()

    def bullets(self, n):
        """Top-level bullets of section n, with their wrapped continuation lines."""
        return [" ".join(b.split()) for b in re.split(r"(?m)^- ", self.sections.get(n, ""))[1:]]


def load_raw():
    pages = [RawPage(p) for p in sorted((DATA / "topics").glob("*/*.md")) if p.name != "README.md"]
    taxonomy = re.findall(r"^\| (\d\d) \| [^|]+\| \[`([^`]+)`\]", (DATA / "TAXONOMY.md").read_text(encoding="utf-8"), re.MULTILINE)
    return {p.id: p for p in pages}, taxonomy


def check_all(data: dict) -> list[dict]:
    raw, taxonomy = load_raw()
    pages = list(raw.values())
    sample = raw[SAMPLE]
    ask = lambda n, **params: answer_question(n, data, params)
    results = []

    def add(n, verdict_ok, verdict, summary, check):
        results.append({"question": n, "verdict": verdict if verdict_ok else "WRONG",
                        "answer": summary, "check": check})

    a = ask(1)["data"]
    add(1, [t["id"] for t in a] == [folder for _, folder in taxonomy], "correct",
        f"{len(a)} topics", "ids and order equal the TAXONOMY.md folders")
    a = ask(2)["data"]
    expected = (len(pages), sum(p.meta.get("status") == "open" for p in pages))
    add(2, (a["total"], a["open"]) == expected, "correct", f"{a['total']} problems, {a['open']} open",
        f"raw pages {expected[0]}, raw status: open {expected[1]}")
    a = {r["topic_id"]: r["problem_count"] for r in ask(3)["data"]}
    add(3, a == dict(Counter(p.topic for p in pages)), "correct", f"35 topics, {min(a.values())}-{max(a.values())} each",
        "per-topic counts equal the files per topic folder")
    a = ask(4)["data"]
    raw_open = Counter(p.topic for p in pages if p.meta.get("status") == "open")
    add(4, {r["topic_id"]: r["open_count"] for r in a} == dict(raw_open), "correct",
        f"most: {a[0]['topic_id']} ({a[0]['open_count']})", "open counts per topic equal raw frontmatter")
    a = {x["id"] for x in ask(5)["data"]}
    add(5, a == {p.id for p in pages if p.meta.get("status") == "solved-but-impractical"}, "correct",
        f"{len(a)} problems", "same ids as raw status: solved-but-impractical")
    a = ask(6, before="2026-07")["data"]
    add(6, len(a) == sum(p.meta.get("last_reviewed", "") < "2026-07" for p in pages), "correct",
        f"{len(a)} last reviewed before 2026-07", "equals raw last_reviewed")
    a = ask(7, problem_id=SAMPLE)["data"]
    add(7, (a["title"], a["status"]) == (sample.meta["title"], sample.meta["status"]), "correct",
        f"{a['title']} ({a['status']})", "title and status equal the sample page frontmatter")
    a = ask(8, problem_id=SAMPLE)["data"]
    add(8, a["id"] == sample.meta["topic"], "correct", a["name"], "equals the page's topic field")
    a = ask(9, problem_id=SAMPLE)["data"]
    tags = [re.match(r"\*\*\[(\w+)\]", b).group(1).casefold() for b in sample.bullets(9)]
    add(9, [e["role"] for e in a] == tags, "limited", f"{len(a)} papers: {', '.join(e['role'] for e in a)}",
        "count and roles equal the page's §9 bullets and tags")
    a = ask(10, problem_id=SAMPLE)["data"]
    add(10, a["upper"][0]["text"] == sample.sections[4] and a["lower"][0]["text"] == sample.sections[5],
        "correct", f"upper/lower bound text, models {sorted({m['model'] for m in a['models']})}",
        "texts equal raw §4 and §5")
    a = ask(11, problem_id=SAMPLE)["data"]
    add(11, a["text"] == sample.sections[6], "correct", f"verdict {a['verdict']} ({a['verdict_method']})",
        "gap text equals raw §6")
    a = ask(12, problem_id=SAMPLE)["data"]
    add(12, bool(a) and all(r["who"].split()[-1] in sample.sections[7] for r in a), "limited",
        f"{len(a)} people", "every returned surname occurs in raw §7")
    inst_pattern = re.compile(next(p for k, _, _, p in INSTITUTIONS if k == INSTITUTION))
    a = ask(27)["data"]
    cmu = next(r["open_problems"] for r in a if r["institution"]["id"] == f"institution:{INSTITUTION}")
    raw_cmu = sum(p.meta.get("status") == "open" and bool(inst_pattern.search(p.sections.get(7, ""))) for p in pages)
    with_inst = next(p for p in pages if inst_pattern.search(p.sections.get(7, "")))
    a13 = ask(13, problem_id=with_inst.id)["data"]
    add(13, "Carnegie Mellon University" in {r["who"] for r in a13}, "limited",
        f"{len(a13)} institution links on {with_inst.id}", "includes CMU, which raw §7 of that page names")
    add(27, cmu == raw_cmu, "limited", f"top: {a[0]['institution']['name']} ({a[0]['open_problems']}); CMU {cmu}",
        f"CMU open problems = raw open pages whose §7 names CMU ({raw_cmu})")
    a = ask(14, problem_id=SAMPLE)["data"]
    add(14, a == sample.sections[10], "correct", f"{len(a)} characters", "equals raw §10")
    a = ask(15, problem_id=SAMPLE)["data"]
    add(15, len(a) == len(sample.bullets(8)), "correct", f"{len(a)} items", "equals the §8 bullet count")
    a = ask(16)["data"][0]
    title = a["paper"]["title"].rstrip(".")
    raw16 = sum(any(title in b for b in p.bullets(9)) for p in pages)
    add(16, a["problem_count"] == raw16, "correct", f"{title} ({a['problem_count']} problems)",
        f"raw pages citing that title: {raw16}")
    a = ask(17)["data"][0]
    title17 = a["paper"]["title"].rstrip(".")
    raw17 = len({p.topic for p in pages if any(title17 in b for b in p.bullets(9))})
    add(17, a["topic_count"] == raw17, "correct", f"{title17} ({a['topic_count']} topics)",
        f"raw topics citing that title: {raw17}")
    a = ask(18)["data"]
    raw18 = sum(b.startswith("**[Survey]**") for p in pages for b in p.bullets(9))
    add(18, sum(r["problem_count"] for r in a) == raw18, "limited", f"{len(a)} survey papers, top {a[0]['paper']['title']}",
        f"survey citations = raw **[Survey]** bullets ({raw18})")
    a = ask(19, after_year=2015)["data"]
    years_ok = all(1900 <= decade <= 2020 for decade in a["by_decade"])
    add(19, years_ok and a["count"] <= sum(a["by_decade"].values()), "limited",
        f"{a['count']} cited papers after 2015", "years are integers between 1900 and 2029")
    a = ask(20)["data"]
    add(20, a[0]["venue"]["name"] == "SIGMOD", "consistent", f"top: {a[0]['venue']['name']} ({a[0]['paper_count']})",
        "same top venue as the 2026-09 graph")
    a = ask(21)["data"]
    raw_text = "\n".join(p.sections.get(9, "") for p in pages).casefold()
    dois = [x["doi"] for x in data["Paper"] if x.get("doi")]
    add(21, all(d.casefold() in raw_text for d in dois), "limited",
        f"DOI {a['doi']}, arXiv {a['arxiv']}, DBLP only {a['dblp_only']}, none {a['none']}",
        "every DOI occurs in the raw §9 text")
    a = ask(22)["data"]
    raw22 = sum(bool(re.search(r"\bunverified\b", b, re.IGNORECASE)) for p in pages for b in p.bullets(9))
    flagged = sum(bool(int(p.meta.get("refs_unverified") or 0)) for p in pages)
    add(22, len(a["citations"]) == raw22 and len(a["pages_with_unidentified"]) <= flagged, "limited",
        f"{len(a['citations'])} marked citations; {len(a['pages_with_unidentified'])} pages give only a count",
        f"marked = raw §9 bullets saying unverified ({raw22}); {flagged} pages carry a count")
    a = ask(23)["data"][:5]
    add(23, all(r["papers"] <= raw_text.count(r["person"]["name"].casefold()) for r in a), "consistent",
        ", ".join(f"{r['person']['name']} ({r['papers']})" for r in a),
        "each top name occurs in raw §9 at least that many times")
    a = ask(24)["data"][:5]
    ok24 = all(r["person"]["name"].split()[-1] in raw[e["problem_id"]].sections.get(7, "")
               for r in a for e in data["ACTIVE_ON"] if e.get("source_node_id") == r["person"]["id"])
    add(24, ok24, "consistent", ", ".join(f"{r['person']['name']} ({r['problems']} problems, {r['topics']} topics)"
                                          for r in a[:3]), "the surname occurs in raw §7 of every linked problem")
    a = ask(25, person_name=PERSON)["data"]
    bullets = [b for p in pages for b in p.bullets(9)]
    ok25 = all(any(r["person"]["name"] in b and "Neumann" in b for b in bullets) for r in a)
    add(25, bool(a) and ok25, "consistent", f"{PERSON}: " + ", ".join(r["person"]["name"] for r in a[:4]),
        "each co-author shares a raw citation with Neumann")
    a = ask(26)
    add(26, a["data"] == [] and a["status"] == "partial", "limited", "no profiles", "DBLP lookup is out of v1 scope")
    a = ask(28)["data"]
    add(28, ["T. Neumann", "Thomas Neumann"] in [[n for n in g if "Neumann" in n] for g in a] or
        any({"T. Neumann", "Thomas Neumann"} <= set(g) for g in a), "limited", f"{len(a)} variant groups",
        "finds T. Neumann / Thomas Neumann as one group")
    for n, label in ((29, "algorithm"), (30, "system")):
        a = ask(n)["data"][:5]
        ok = all(r["problems"] <= sum(r[label]["name"].casefold() in p.sections.get(3, "").casefold() for p in pages)
                 for r in a)
        add(n, ok, "limited", ", ".join(f"{r[label]['name']} ({r['problems']})" for r in a[:4]),
            "each top name occurs in raw §3 of at least that many pages")
    a = ask(31, problem_id=SAMPLE)["data"]
    add(31, all(x.casefold() in sample.sections[3].casefold() for k in a for x in a[k]), "correct",
        f"theory {a['theory']}, systems {a['systems']}", "every name occurs in raw §3")
    a = ask(32)["data"]
    pattern = re.compile(r"\bSETH\b|\b3SUM\b|\bAPSP\b|\bOMv\b|fine[- ]grained (?:complexity|hardness|lower bound)s?", re.IGNORECASE)
    raw32 = {p.id for p in pages if pattern.search(p.sections.get(5, ""))}
    add(32, set(a) == raw32, "correct", f"{len(a)} problems", "equals raw pages whose §5 names SETH/3SUM/APSP/OMv")
    a = ask(33)["data"]
    add(33, sum(a.values()) == sum(bool(p.sections.get(4)) + bool(p.sections.get(5)) for p in pages), "consistent",
        ", ".join(f"{k} {v}" for k, v in a.items()), "one kind per non-empty raw §4/§5")
    a = ask(34)["data"]
    add(34, all(re.search(r"closed|tight|match|settled|resolved|no (?:asymptotic )?gap", g["text"], re.IGNORECASE) for g in a),
        "limited", f"{len(a)} closed gaps", "every one has closing wording in raw §6")
    a = ask(35, problem_id=SAMPLE)["data"]
    cites = defaultdict(set)
    for e in data["CITES"]:
        cites[e["problem_id"]].add(e["target_id"])
    add(35, all(cites[SAMPLE] & cites[r["problem"]] for r in a), "consistent", f"{len(a)} related problems",
        "each shares at least one cited paper")
    a = ask(36)["data"]
    topic_of = {p.id: p.topic for p in pages}
    cross = sum(topic_of[e["problem_id"]] != topic_of[e["target_id"]] for e in data["RELATED_TO"])
    add(36, sum(r["links"] for r in a) == cross, "consistent", f"top pair {a[0]['topics']} ({a[0]['links']})",
        "pair counts sum to the cross-topic links")
    a = ask(37, concept=CONCEPT)["data"]
    alias = re.compile("|".join(re.escape(x) for x in CONCEPTS[CONCEPT]))
    raw37 = sum(bool(alias.search(p.sections.get(2, ""))) for p in pages)
    add(37, a[0]["problems"] == raw37, "limited", f"{CONCEPT}: {a[0]['problems']} problems",
        f"raw pages whose §2 names it: {raw37}")
    a = ask(38)["data"]
    add(38, {(r["broader"], r["narrower"]) for r in a} <= {(x, y) for x, y, _ in CONCEPT_HIERARCHY} and len(a) == 31,
        "limited", f"{len(a)} broader/narrower pairs", "all are reviewed pairs")
    a = ask(39)
    add(39, a["data"] == [] and a["status"] == "partial", "limited", "no ranking", "vector search not available")
    a = ask(40)["data"]
    add(40, a[0]["other_topics"] >= a[-1]["other_topics"], "consistent",
        f"top: {a[0]['problem']} ({a[0]['other_topics']} other topics)", "ranked by distinct linked topics")
    a = ask(41)["data"]
    add(41, all(g["verdict"] == "open" and raw[g["problem_id"]].meta["status"] == "open" for g in a), "limited",
        f"{len(a)} open problems with an open gap", "verdict open and raw status open")
    a = ask(42)["data"]
    linked = {e["problem_id"] for e in data["ACTIVE_ON"] if e["source_label"] == "Person"}
    add(42, all(x["id"] not in linked and raw[x["id"]].meta["status"] == "open" for x in a), "limited",
        f"{len(a)} open problems", "none has a linked person; all open in raw")
    a = {r["topic_id"]: r["future_work_count"] for r in ask(43)["data"]}
    raw43 = Counter()
    for p in pages:
        raw43[p.topic] += len(p.bullets(8))
    add(43, a == dict(raw43), "correct", f"top {max(a, key=a.get)} ({max(a.values())})", "equals raw §8 bullets per topic")
    a = ask(44)["data"]
    add(44, all(len({x["problem_id"] for x in g}) > 1 for g in a), "limited", f"{len(a)} shared items",
        "exact-text matches only")
    a = ask(45, before_year=2015)["data"]
    years = {x["id"]: x.get("year") for x in data["Paper"]}
    add(45, all(all(not isinstance(years[t], int) or years[t] <= 2015 for t in cites[x["id"]]) for x in a), "limited",
        f"{len(a)} open problems", "no cited paper after 2015")
    for n in (46, 47, 48):
        a = ask(n)
        add(n, a["status"] == "refusal" and a["data"] == [], "refused", "refused", a["reason"])
    return sorted(results, key=lambda r: r["question"])


def render(results: list[dict]) -> str:
    counts = Counter(r["verdict"] for r in results)
    scope = (ROOT / "docs" / "scope.md").read_text(encoding="utf-8")
    text = dict(re.findall(r"^(\d+)\. (.+?)(?: \*\*\[|$)", scope, re.MULTILINE))
    lines = ["# Question report: the 48 scope questions on the catalog-built graph", "",
             ("Generated by `python -m etl.question_check`. Each answer is compared with a value read from "
             "the raw pages in `data/dbms_research` (not through the graph parser), or, for computed links, "
             "checked against the graph's own evidence."), "",
             "**" + ", ".join(f"{v} {k}" for k, v in counts.most_common()) + f" (of {len(results)})**", "",
             "| # | Question | Verdict | Answer | Check |", "|---|---|---|---|---|"]
    for r in results:
        q = text.get(str(r["question"]), "").replace("|", "/")
        lines.append(f"| {r['question']} | {q} | {r['verdict']} | {r['answer']} | {r['check']} |".replace("\n", " "))
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    from etl.loader import prepare
    data = prepare(json.loads(CATALOG.read_text(encoding="utf-8")))
    results = check_all(data)
    for r in results:
        print(f"{r['question']:>2} {r['verdict']:10} {r['answer'][:90]}")
    if args.report:
        args.report.write_text(render(results), encoding="utf-8")
    assert [r["question"] for r in results] == list(QUESTION_IDS)
    return 0 if all(r["verdict"] != "WRONG" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
