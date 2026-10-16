"""Load the validated DBMS Research catalog into an isolated Samyama instance."""
from __future__ import annotations

import argparse
import collections
import hashlib
import itertools
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

from samyama import SamyamaClient
from etl.citations import parse_citation, paper_identity, person_key
from etl.source_entities import (ALGORITHMS, SYSTEMS, matching_concepts,
                                 matching_models, matching_terms)

PINNED_COMMIT = "5fff7f74508a52ac238f3bb608b8c8c872489fec"


def stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}:{digest}"


def cypher_string(value) -> str:
    """Encode a Python value as a Cypher string literal."""
    value = "" if value is None else str(value)
    value = value.replace("\\", "\\\\").replace("'", "\\'")
    value = value.replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")
    return "'" + value + "'"


def chunks(items, size):
    for start in range(0, len(items), size):
        yield items[start:start + size]


def cypher_map(record):
    return "{" + ", ".join(
        f"{key}: {cypher_literal(value)}"
        for key, value in record.items()
    ) + "}"


def cypher_literal(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return cypher_string(value)


def unique_records(records):
    seen = set()
    result = []
    for record in records:
        if record["id"] not in seen:
            seen.add(record["id"])
            result.append(record)
    return result


def bound_kind(text):
    folded = text.casefold()
    if any(term in folded for term in ("space complexity", "space bound", "space usage")):
        return "space"
    if any(term in folded for term in ("impossible", "impossibility", "cannot be solved")):
        return "impossibility"
    if any(term in folded for term in ("time complexity", "time bound", "running time")):
        return "time"
    return "unclassified"


def person_name_form(name):
    value = name.strip()
    if re.fullmatch(r"(?:[A-Z]\.\s*)+", value):
        return "initials"
    if re.fullmatch(r"(?:[A-Z]\.\s*)+[A-Z][A-Za-z'’\-]+", value):
        return "initials"
    if len(value.split()) == 1:
        return "surname"
    return "full"


def venue_kind(name):
    folded = name.casefold()
    if any(term in folded for term in ("arxiv", "arxiv preprint", "preprint")):
        return "preprint"
    if any(term in folded for term in ("journal", "transactions", "j. ", "j. of")):
        return "journal"
    if any(term in folded for term in ("conference", "proceedings", "sigmod", "vldb", "pods", "icde", "edbt", "soda")):
        return "conference"
    return "other"


def gap_verdict(text):
    """Conservative §6 verdict with an auditable rule label."""
    value = text.strip()
    stated = re.match(r"\s*\*\*(open|partially[- ]solved|empirically[- ]open|closed)\*\*", value, re.I)
    if stated:
        return stated.group(1).casefold().replace(" ", "-"), "stated"
    folded = value.casefold()
    if not folded:
        return "unstated", "none"
    if re.search(r"\b(no|not|isn't|is not)\s+(open|closed)\b", folded):
        return "unstated", "none"
    if re.search(r"\b(closed|tight bounds?|bounds? match|matching bounds?)\b", folded):
        return "closed", "keyword"
    if re.search(r"\b(empirically open|empirical gap)\b", folded):
        return "empirically-open", "keyword"
    if re.search(r"\b(partially solved|partially-closed)\b", folded):
        return "partially-solved", "keyword"
    if re.search(r"\b(open|unknown|remains unresolved|is unresolved)\b", folded):
        return "open", "keyword"
    return "unstated", "none"


def classify_problem_type(problem):
    text = " ".join((problem.get("title", ""),
                     problem.get("sections", {}).get("problem_statement", ""))).casefold()
    rules = (
        ("query-optimization", r"\b(query optimization|query optimizer|plan selection)\b"),
        ("query-evaluation", r"\b(query evaluation|query processing|join evaluation)\b"),
        ("data-modeling", r"\b(data model|schema design|normal form|dependency)\b"),
        ("data-integration", r"\b(data integration|data exchange|schema mapping)\b"),
        ("transaction-processing", r"\b(transaction|serializability|concurrency control)\b"),
        ("storage-indexing", r"\b(storage|indexing|index structure|data layout)\b"),
        ("distributed-data", r"\b(distributed|replication|sharding|consensus)\b"),
        ("analytics", r"\b(analytics|aggregation|machine learning)\b"),
        ("system-design", r"\b(database system|dbms architecture|self-driving)\b"),
    )
    matches = [code for code, pattern in rules if re.search(pattern, text)]
    return (matches[0], "rule-based") if matches else ("unclassified", "unresolved")


def classification_evidence(problem):
    statement = (problem.get("sections", {}).get("problem_statement")
                 or problem.get("problem_statement", ""))
    return "\n".join((problem.get("title", ""),
                      statement)).strip()


def model_class(name):
    key = name.casefold()
    if "word-ram" in key: return "word-ram"
    if "cell-probe" in key: return "cell-probe"
    if "external" in key or "i/o" in key: return "external-memory"
    if "comparison" in key: return "comparison"
    if "stream" in key: return "streaming"
    if "pram" in key or "parallel" in key: return "parallel"
    if "turing" in key: return "turing"
    return "unclassified"


def technique_family(name, entity_type):
    folded = name.casefold()
    if entity_type == "Algorithm":
        if any(x in folded for x in ("yannakakis", "join", "leapfrog", "insideout", "inside-out", "generic")):
            return "join-processing"
        if any(x in folded for x in ("gyo", "decomposition", "acyclic")):
            return "decomposition"
        return "unclassified"
    if any(x in folded for x in ("duckdb", "umbra", "hyper", "monetdb", "bigquery", "snowflake", "redshift")):
        return "analytical-dbms"
    if any(x in folded for x in ("spark", "trino", "presto")):
        return "distributed-processing"
    if "stream" in folded:
        return "streaming-system"
    if any(x in folded for x in ("mysql", "postgres", "sqlite", "mariadb", "cockroach", "tidb")):
        return "relational-dbms"
    return "unclassified"


def annotate_provenance(records, *, source, default_method="parsed"):
    commit = source.get("actual_commit", PINNED_COMMIT)
    retrieved = source.get("retrieved_at") or "unknown"
    source_date = source.get("source_date") or "unknown"
    for record in records:
        path = record.get("source_path") or "README.md"
        record.setdefault("provenance", "real")
        record.setdefault("source", "dbms_research")
        record.setdefault("method", default_method)
        record.setdefault("retrieved_at", retrieved)
        record.setdefault("source_date", source_date)
        record.setdefault("source_url", f"https://github.com/samyama-ai/dbms_research/blob/{commit}/{path}")
    return records


def prepare(catalog):
    from etl.conformance import load_spec

    mapping_spec = load_spec()
    artifact_mappings = {
        url.casefold(): value
        for url, value in mapping_spec.get("artifact_citation_mappings", {}).items()
    }
    source = catalog.get("source", {})
    topics = []
    for topic in catalog["topics"]:
        topic_id = topic["id"]
        topics.append({
            "id": topic_id,
            "number": topic_id[:2],
            "slug": topic_id,
            "name": topic.get("title") or topic["id"],
            "scope": topic.get("scope", ""),
            "source_path": topic["source_path"],
        })

    problems = []
    papers_by_id = {}
    paper_ids_by_identity = {}
    people_by_id = {}
    venues_by_id = {}
    algorithms_by_id = {}
    systems_by_id = {}
    concepts_by_id = {}
    models_by_id = {}
    citations = []
    authorships = []
    appearances = []
    sota_edges = []
    rests_on_edges = []
    model_edges = []
    bounds = []
    future_directions = []
    bound_edges = []
    future_edges = []
    gaps = []
    gap_edges = []
    research_directions = []
    research_edges = []
    active_edges = []

    # Build source-visible author name candidates before parsing §7 so mentions
    # can be linked only when the exact authored form occurs in the same page.
    author_candidates = {}
    for source_problem in catalog["problems"]:
        for raw_ref in source_problem.get("reference_entries", []):
            parsed_author = parse_citation(raw_ref, bool(source_problem.get("metadata", {}).get("refs_unverified")))
            for author_name in parsed_author["authors"]:
                author_candidates.setdefault(person_key(author_name), author_name)
    authors_by_surname = {}
    for author_key, author_name in author_candidates.items():
        surname = author_key.split()[-1] if author_key.split() else ""
        authors_by_surname.setdefault(surname, []).append((author_key, author_name))

    for problem in catalog["problems"]:
        meta = problem["metadata"]
        sections = problem["sections"]
        pid = problem["id"]

        problems.append({
            "id": pid,
            "slug": pid.rsplit("/", 1)[-1],
            "title": problem["title"],
            "status": problem["status"],
            "problem_type": classify_problem_type(problem)[0],
            "classification_evidence_status": classify_problem_type(problem)[1],
            "topic_id": problem["topic_id"],
            "source_path": problem["source_path"],
            "first_added": meta.get("first_added", ""),
            "last_reviewed": meta.get("last_reviewed", ""),
            "last_substantive_update": meta.get("last_substantive_update", ""),
            "stale_since": meta.get("stale_since", ""),
            "catalog_provenance": meta.get("provenance", ""),
            "refs_checked": meta.get("refs_checked", ""),
            "refs_unverified": bool(meta.get("refs_unverified", False)),
            "problem_statement": sections.get("problem_statement", ""),
            "statement": sections.get("problem_statement", ""),
            "mathematical_foundations": sections.get("mathematical_foundations", ""),
            "state_of_the_art": sections.get("state_of_the_art", ""),
            "upper_bound_text": sections.get("upper_bound", ""),
            "lower_bound_text": sections.get("lower_bound", ""),
            "gap_text": sections.get("gap", ""),
            "current_research": sections.get("current_research", ""),
            "future_work_text": sections.get("future_work", ""),
            "worked_example": sections.get("worked_example", ""),
            "key_references": sections.get("key_references", ""),
        })

        for kind in ("upper", "lower"):
            text = sections.get(f"{kind}_bound", "").strip()
            if not text:
                continue
            bid = f"bound:{pid}:{kind}"
            bounds.append({
                "id": bid,
                "problem_id": pid,
                "direction": kind,
                "kind": bound_kind(text),
                "text": text,
                "source_path": problem["source_path"],
            })
            bound_edges.append({"problem_id": pid, "target_id": bid,
                                "direction": kind})

        # Preserve the original loader's zero-based index: these IDs already
        # exist in the partially loaded graph and are the canonical IDs.
        for index, item in enumerate(problem["future_work_items"]):
            item = item.strip()
            if not item:
                continue
            fid = stable_id("future", f"{pid}\n{index}\n{item}")
            future_directions.append({
                "id": fid,
                "problem_id": pid,
                "text": item,
                "source_path": problem["source_path"],
            })
            future_edges.append({"problem_id": pid, "target_id": fid,
                                 "position": index})

        gap_text = sections.get("gap", "").strip()
        verdict, verdict_method = gap_verdict(gap_text)
        gap_id = f"{pid}#gap"
        gaps.append({"id": gap_id, "problem_id": pid, "text": gap_text,
                     "verdict": verdict, "verdict_raw": gap_text[:160],
                     "verdict_method": verdict_method, "source_path": problem["source_path"]})
        gap_edges.append({"problem_id": pid, "target_id": gap_id})

        research_items = [x.strip() for x in re.split(r"\n(?=\s*(?:[-*+] |\d+[.)] ))", sections.get("current_research", "")) if x.strip()]
        for position, item in enumerate(research_items, 1):
            rid = f"{pid}#research-{position}"
            frontier = "frontier — verify" in item.casefold()
            research_directions.append({"id": rid, "problem_id": pid, "text": item,
                "frontier": frontier, "source_path": problem["source_path"]})
            research_edges.append({"problem_id": pid, "target_id": rid, "position": position})
            normalized_item = " " + person_key(item) + " "
            capitalized_tokens = {x.casefold() for x in re.findall(r"(?<!\w)[A-Z][A-Za-z'’-]+", item)}
            for surname in capitalized_tokens:
                for person_key_value, author_name in authors_by_surname.get(surname, []):
                    if " " + person_key_value + " " not in normalized_item:
                        continue
                    person_id = stable_id("person", person_key_value)
                    people_by_id.setdefault(person_id, {"id": person_id, "name": author_name,
                        "name_form": person_name_form(author_name), "source_path": problem["source_path"]})
                    active_edges.append({"source_node_id": person_id, "source_label": "Person",
                        "target_id": pid, "problem_id": pid, "direction": item})

        for concept in matching_concepts(sections.get("mathematical_foundations", "")):
            cid = stable_id("concept", concept.casefold())
            concepts_by_id.setdefault(cid, {"id": cid, "name": concept,
                "source_path": problem["source_path"], "extraction": "allowlisted_source_phrase"})
            rests_on_edges.append({"problem_id": pid, "concept_id": cid})

        sota_text = sections.get("state_of_the_art", "")
        for name in matching_terms(sota_text, list(SYSTEMS)):
            sid = stable_id("system", name.casefold())
            systems_by_id.setdefault(sid, {"id": sid, "name": name,
                "kind": "database-system",
                "family": technique_family(name, "System"),
                "source_path": problem["source_path"], "extraction": "allowlisted_source_phrase"})
            sota_edges.append({"problem_id": pid, "target_id": sid, "kind": "systems",
                               "target_label": "System"})
        for name in matching_terms(sota_text, list(ALGORITHMS)):
            aid = stable_id("algorithm", name.casefold())
            algorithms_by_id.setdefault(aid, {"id": aid, "name": name,
                "family": technique_family(name, "Algorithm"),
                "source_path": problem["source_path"], "extraction": "allowlisted_source_phrase"})
            sota_edges.append({"problem_id": pid, "target_id": aid, "kind": "theory",
                               "target_label": "Algorithm"})

        for kind in ("upper", "lower"):
            for model in matching_models(sections.get(f"{kind}_bound", "")):
                mid = stable_id("model", model.casefold())
                models_by_id.setdefault(mid, {"id": mid, "name": model,
                    "class": model_class(model),
                    "source_path": problem["source_path"], "extraction": "allowlisted_source_phrase"})
                bid = f"bound:{pid}:{kind}"
                if any(b["id"] == bid for b in bounds):
                    model_edges.append({"bound_id": bid, "model_id": mid})

        for citation_position, raw_ref in enumerate(problem["reference_entries"], 1):
            parsed = parse_citation(raw_ref, bool(meta.get("refs_unverified")))
            text = parsed["citation_normalized"]
            if not text:
                continue
            identity = paper_identity(parsed)
            # Retain the legacy full-citation id for the first source occurrence.
            # The catalog order is deterministic and this id already exists in
            # the partially populated graph. Alternate citations reuse it.
            paper_id = paper_ids_by_identity.setdefault(
                identity, stable_id("paper", text.casefold()))
            paper_metadata = {k: v for k, v in parsed.items()
                              if k not in {"role", "role_raw", "role_status", "verification_status",
                                           "citation_normalized"}}
            paper_record = {"id": paper_id, **paper_metadata,
                            "authors": "; ".join(parsed["authors"]),
                            "authors_raw": parsed["authors_raw"],
                            "source_path": problem["source_path"]}
            papers_by_id.setdefault(paper_id, paper_record)
            cito_property = mapping_spec.get("cito_roles", {}).get(parsed["role"], "cites")
            citation_mapping = {}
            citation_url = parsed.get("url", "").casefold().rstrip("/")
            if parsed["role"] == "artifact":
                artifact_mapping = artifact_mappings.get(citation_url)
                if artifact_mapping:
                    cito_property = artifact_mapping["cito_property"]
                    citation_mapping = {
                        "artifact_kind": artifact_mapping["artifact_kind"],
                        "cito_mapping_note": artifact_mapping["note"],
                    }
                else:
                    citation_mapping = {
                        "artifact_kind": "unspecified",
                        "cito_mapping_note": "No source-specific mapping is configured; generic cito:cites fallback is used.",
                    }
            citations.append({"problem_id": pid, "paper_id": paper_id,
                             "position": citation_position,
                             "role": parsed["role"], "role_raw": parsed["role_raw"],
                             "role_status": parsed["role_status"],
                             "verification_status": parsed["verification_status"],
                             "cito_property": cito_property,
                             **citation_mapping})
            for position, author in enumerate(parsed["authors"], 1):
                person_id = stable_id("person", person_key(author))
                people_by_id.setdefault(person_id, {"id": person_id, "name": author,
                    "name_form": person_name_form(author), "source_path": problem["source_path"]})
                authorships.append({"paper_id": paper_id, "person_id": person_id,
                                    "position": position})
            if parsed["venue_raw"]:
                venue_id = stable_id("venue", parsed["venue_raw"].casefold())
                venues_by_id.setdefault(venue_id, {"id": venue_id,
                    "name": parsed["venue_raw"], "kind": venue_kind(parsed["venue_raw"]),
                    "source_path": problem["source_path"]})
                appearances.append({"paper_id": paper_id, "venue_id": venue_id})

    data = {
        "Topic": unique_records(topics),
        "Problem": unique_records(problems),
        "Paper": list(papers_by_id.values()),
        "Person": list(people_by_id.values()),
        "Venue": list(venues_by_id.values()),
        "Algorithm": list(algorithms_by_id.values()),
        "System": list(systems_by_id.values()),
        "Concept": list(concepts_by_id.values()),
        "ComputationModel": list(models_by_id.values()),
        "Bound": unique_records(bounds),
        "FutureDirection": unique_records(future_directions),
        "Gap": unique_records(gaps),
        "ResearchDirection": unique_records(research_directions),
        "Institution": [],
        "DataSource": [{"id": "datasource:dbms_research",
            "name": "DBMS Research problem catalog",
            "url": source.get("repository", "https://github.com/samyama-ai/dbms_research"),
            "version": source.get("actual_commit", PINNED_COMMIT),
            "licence": "CC BY 4.0", "source_path": "README.md", "method": "catalog"}],
        "TaxonomyTerm": [],
        "IN_TOPIC": unique_records([
            {"id": f"{p['id']}->{p['topic_id']}",
             "problem_id": p["id"], "target_id": p["topic_id"]}
            for p in problems
        ]),
        "HAS_BOUND": unique_records([
            {"id": f"{e['problem_id']}->{e['target_id']}", **e}
            for e in bound_edges
        ]),
        "CLOSING_REQUIRES": unique_records([
            {"id": f"{e['problem_id']}->{e['target_id']}", **e}
            for e in future_edges
        ]),
        "CITES": unique_records([
            {"id": f"{e['problem_id']}->{e['paper_id']}",
             "problem_id": e["problem_id"],
             "target_id": e["paper_id"], "role": e["role"],
             "role_raw": e["role_raw"],
             "role_status": e["role_status"],
             "position": e["position"],
             "verification_status": e["verification_status"],
             "cito_property": e["cito_property"],
             **{key: e[key] for key in ("artifact_kind", "cito_mapping_note") if key in e}}
            for e in citations
        ]),
        "AUTHORED_BY": unique_records([
            {"id": f"{e['paper_id']}->{e['person_id']}",
             "paper_id": e["paper_id"], "target_id": e["person_id"],
             "position": e["position"]}
            for e in authorships
        ]),
        "APPEARED_AT": unique_records([
            {"id": f"{e['paper_id']}->{e['venue_id']}",
             "paper_id": e["paper_id"], "target_id": e["venue_id"]}
            for e in appearances
        ]),
        "STATE_OF_ART": unique_records([
            {"id": f"{e['problem_id']}->{e['target_id']}", **e}
            for e in sota_edges
        ]),
        "RESTS_ON": unique_records([
            {"id": f"{e['problem_id']}->{e['concept_id']}",
             "problem_id": e["problem_id"], "target_id": e["concept_id"]}
            for e in rests_on_edges
        ]),
        "IN_MODEL": unique_records([
            {"id": f"{e['bound_id']}->{e['model_id']}",
             "bound_id": e["bound_id"], "target_id": e["model_id"]}
            for e in model_edges
        ]),
        "HAS_GAP": unique_records([{"id": f"{e['problem_id']}->{e['target_id']}", **e} for e in gap_edges]),
        "HAS_RESEARCH": unique_records([{"id": f"{e['problem_id']}->{e['target_id']}", **e} for e in research_edges]),
        "ACTIVE_ON": unique_records([{"id": f"{e['source_node_id']}->{e['target_id']}", **e}
                                     for e in active_edges]),
        "AFFILIATED_WITH": [],
        "GENERALIZES": [],
        "RELATED_TO": [],
        "FROM_SOURCE": unique_records([{"id": f"{p['id']}->datasource:dbms_research",
            "problem_id": p["id"], "target_id": "datasource:dbms_research"} for p in problems]),
        "CLASSIFIED_AS": [],
    }

    # RELATED_TO is computed only from identifiable shared catalog evidence.
    # A pair needs at least two distinct shared papers/concepts, so a single
    # ubiquitous citation cannot create an edge by itself.
    evidence_by_problem = collections.defaultdict(set)
    for edge in data["CITES"]:
        evidence_by_problem[edge["problem_id"]].add(("paper", edge["target_id"]))
    for edge in data["RESTS_ON"]:
        evidence_by_problem[edge["problem_id"]].add(("concept", edge["target_id"]))
    evidence_to_problems = collections.defaultdict(set)
    for problem_id, evidence_items in evidence_by_problem.items():
        for evidence_item in evidence_items:
            evidence_to_problems[evidence_item].add(problem_id)
    shared_by_pair = collections.defaultdict(set)
    for evidence_item, problem_ids in evidence_to_problems.items():
        for left, right in itertools.combinations(sorted(problem_ids), 2):
            shared_by_pair[(left, right)].add(evidence_item)
    problem_by_id = {p["id"]: p for p in data["Problem"]}
    for (left, right), shared in sorted(shared_by_pair.items()):
        if len(shared) < 2:
            continue
        union = evidence_by_problem[left] | evidence_by_problem[right]
        shared_papers = sum(kind == "paper" for kind, _ in shared)
        shared_concepts = sum(kind == "concept" for kind, _ in shared)
        paths = sorted({problem_by_id[x]["source_path"] for x in (left, right)})
        urls = [f"https://github.com/samyama-ai/dbms_research/blob/{PINNED_COMMIT}/{path}"
                for path in paths]
        data["RELATED_TO"].append({
            "id": f"{left}->{right}", "problem_id": left, "target_id": right,
            "method": "shared-papers-concepts",
            "score": round(len(shared) / len(union), 6),
            "shared_evidence_count": len(shared),
            "shared_papers": shared_papers, "shared_concepts": shared_concepts,
            "source_commit": PINNED_COMMIT, "source_urls": urls,
        })

    spec_path = Path(__file__).resolve().parents[1] / "schema" / "conformance.json"
    code_lists = json.loads(spec_path.read_text(encoding="utf-8"))["codes"]
    taxonomy_terms = {}

    def add_term(scheme, code, label):
        key = (scheme, code)
        if key not in taxonomy_terms:
            term_id = stable_id("taxonomy", scheme + "\n" + code)
            taxonomy_terms[key] = {"id": term_id, "scheme": scheme, "code": code,
                "name": label, "notation": code,
                "provenance": "schema-vocabulary", "source": "project_schema",
                "method": "list-matched", "retrieved_at": source.get("retrieved_at", "unknown"),
                "source_date": source.get("source_date", "unknown"),
                "source_url": "docs/schema.md"}
        return taxonomy_terms[key]["id"]

    for topic in data["Topic"]:
        add_term("dbms-topic", topic["id"], topic["name"])
    for code in code_lists["Problem.problem_type"]:
        add_term("problem-type", code, code.replace("-", " "))
    for code in code_lists["Algorithm.family|System.family"]:
        add_term("solution-technique-family", code, code.replace("-", " "))
    for code in code_lists["ComputationModel.class"]:
        add_term("computation-model-workload", code, code.replace("-", " "))
    data["TaxonomyTerm"] = list(taxonomy_terms.values())

    def classify(source_id, source_label, scheme, code, evidence_status, evidence):
        target_id = add_term(scheme, code, code.replace("-", " "))
        data["CLASSIFIED_AS"].append({
            "id": f"{source_id}->{target_id}", "source_node_id": source_id,
            "source_label": source_label, "target_id": target_id,
            "evidence_status": evidence_status, "evidence": evidence,
        })

    for p in data["Problem"]:
        classify(p["id"], "Problem", "problem-type", p["problem_type"],
                 p["classification_evidence_status"], classification_evidence(p))
        classify(p["id"], "Problem", "dbms-topic", p["topic_id"],
                 "source-explicit", p["topic_id"])
    for label in ("Algorithm", "System"):
        for node in data[label]:
            classify(node["id"], label, "solution-technique-family", node["family"],
                     "rule-based" if node["family"] != "unclassified" else "unresolved",
                     node["name"])
    for node in data["ComputationModel"]:
        classify(node["id"], "ComputationModel", "computation-model-workload", node["class"],
                 "rule-based" if node["class"] != "unclassified" else "unresolved",
                 node["name"])
    pages_by_paper = {}
    for edge in data["CITES"]:
        pages_by_paper.setdefault(edge["target_id"], set()).add(edge["problem_id"])
    pages_by_entity = {label: {} for label in ("Paper", "Person", "Venue", "Concept", "Algorithm", "System", "ComputationModel")}
    for edge in data["CITES"]:
        pages_by_entity["Paper"].setdefault(edge["target_id"], set()).add(edge["problem_id"])
    for edge in data["AUTHORED_BY"]:
        pages_by_entity["Person"].setdefault(edge["target_id"], set()).update(pages_by_paper.get(edge["paper_id"], set()))
    for edge in data["APPEARED_AT"]:
        pages_by_entity["Venue"].setdefault(edge["target_id"], set()).update(pages_by_paper.get(edge["paper_id"], set()))
    for edge in data["RESTS_ON"]:
        pages_by_entity["Concept"].setdefault(edge["target_id"], set()).add(edge["problem_id"])
    for edge in data["STATE_OF_ART"]:
        pages_by_entity[edge["target_label"]].setdefault(edge["target_id"], set()).add(edge["problem_id"])
    bound_problem = {b["id"]: b["problem_id"] for b in data["Bound"]}
    for edge in data["IN_MODEL"]:
        if edge["bound_id"] in bound_problem:
            pages_by_entity["ComputationModel"].setdefault(edge["target_id"], set()).add(bound_problem[edge["bound_id"]])
    for label, pages in pages_by_entity.items():
        for node in data[label]:
            node["page_count"] = len(pages.get(node["id"], set())) or 1
    # Shared entities retain the first source page and count distinct source pages.
    for label, records in data.items():
        if label in {"IN_TOPIC", "HAS_BOUND", "CLOSING_REQUIRES", "CITES", "AUTHORED_BY",
                     "APPEARED_AT", "STATE_OF_ART", "RESTS_ON", "IN_MODEL", "HAS_GAP",
                     "HAS_RESEARCH", "ACTIVE_ON", "AFFILIATED_WITH", "GENERALIZES",
                     "RELATED_TO", "FROM_SOURCE", "CLASSIFIED_AS"}:
            continue
        method = "list-matched" if label in {"Topic", "Concept", "Algorithm", "System", "ComputationModel", "TaxonomyTerm", "Institution"} else "parsed"
        annotate_provenance(records, source=source, default_method=method)
    node_labels = set(json.loads(spec_path.read_text(encoding="utf-8"))["labels"])
    node_source_paths = {
        record["id"]: record.get("source_path")
        for label, records in data.items() if label in node_labels
        for record in records if isinstance(record, dict) and record.get("id")
    }
    for rel, edges in data.items():
        if rel in {"IN_TOPIC", "HAS_BOUND", "CLOSING_REQUIRES", "CITES", "AUTHORED_BY",
                   "APPEARED_AT", "STATE_OF_ART", "RESTS_ON", "IN_MODEL", "HAS_GAP",
                   "HAS_RESEARCH", "ACTIVE_ON", "AFFILIATED_WITH", "GENERALIZES",
                   "RELATED_TO", "FROM_SOURCE", "CLASSIFIED_AS"}:
            for edge in edges:
                if rel == "RELATED_TO":
                    urls = edge["source_urls"]
                    edge["source_url"] = urls[0]
                    edge["source"] = "dbms_research"
                else:
                    source_id = (edge.get("problem_id") or edge.get("paper_id")
                                 or edge.get("bound_id") or edge.get("source_node_id")
                                 or edge.get("person_id") or edge.get("institution_id"))
                    source_path = node_source_paths.get(source_id)
                    if source_path:
                        edge["source_url"] = (
                            f"https://github.com/samyama-ai/dbms_research/blob/{PINNED_COMMIT}/{source_path}")
                    edge["source"] = "dbms_research"
                    edge.setdefault("method", "parsed")
                    edge["source_commit"] = PINNED_COMMIT
    return data


def print_plan(data):
    print("=== Load plan ===")
    from etl.conformance import load_spec, summarize
    for label in load_spec()["labels"]:
        print(f"{label:18} {len(data[label]):>7,} nodes")
    print()
    for rel in load_spec()["relationships"]:
        print(f"{rel:18} {len(data[rel]):>7,} relationships")
    labels = tuple(load_spec()["labels"])
    relationships = tuple(load_spec()["relationships"])
    print(f"\n{'TOTAL':18} {sum(len(data[x]) for x in labels):>7,} planned node records")
    print(f"{'TOTAL':18} {sum(len(data[x]) for x in relationships):>7,} planned edge records")
    print("\nCitation metadata is parsed from source text and retains the raw citation; "
          "source parsing is not independent bibliographic verification.")


def create_nodes(client, label, records, batch_size):
    if not records:
        return
    for batch in chunks(records, batch_size):
        rows = "[" + ", ".join(cypher_map(row) for row in batch) + "]"
        query = (f"UNWIND {rows} AS row MERGE (n:{label} {{id: row.id}}) "
                 f"SET n += row")
        client.query(query)


def create_relationships(client, rel_type, records, batch_size):
    if not records:
        return
    if rel_type == "STATE_OF_ART" and len({r["target_label"] for r in records}) > 1:
        for label in ("Algorithm", "System"):
            typed = [r for r in records if r["target_label"] == label]
            if typed:
                create_relationships(client, rel_type, typed, batch_size)
        if any(r["target_label"] not in {"Algorithm", "System"} for r in records):
            raise ValueError("STATE_OF_ART has an unsupported target label")
        return
    if rel_type == "CLASSIFIED_AS" and len({r["source_label"] for r in records}) > 1:
        for label in {r["source_label"] for r in records}:
            create_relationships(client, rel_type,
                                 [r for r in records if r["source_label"] == label], batch_size)
        return
    if rel_type == "ACTIVE_ON" and len({r["source_label"] for r in records}) > 1:
        for label in {r["source_label"] for r in records}:
            create_relationships(client, rel_type,
                                 [r for r in records if r["source_label"] == label], batch_size)
        return
    if rel_type == "IN_TOPIC":
        source_label, target_label = "Problem", "Topic"
    elif rel_type == "HAS_BOUND":
        source_label, target_label = "Problem", "Bound"
    elif rel_type == "CLOSING_REQUIRES":
        source_label, target_label = "Problem", "FutureDirection"
    elif rel_type == "CITES":
        source_label, target_label = "Problem", "Paper"
    elif rel_type == "AUTHORED_BY":
        source_label, target_label = "Paper", "Person"
    elif rel_type == "APPEARED_AT":
        source_label, target_label = "Paper", "Venue"
    elif rel_type == "STATE_OF_ART":
        source_label, target_label = "Problem", records[0]["target_label"]
    elif rel_type == "RESTS_ON":
        source_label, target_label = "Problem", "Concept"
    elif rel_type == "IN_MODEL":
        source_label, target_label = "Bound", "ComputationModel"
    elif rel_type == "HAS_GAP":
        source_label, target_label = "Problem", "Gap"
    elif rel_type == "HAS_RESEARCH":
        source_label, target_label = "Problem", "ResearchDirection"
    elif rel_type == "FROM_SOURCE":
        source_label, target_label = "Problem", "DataSource"
    elif rel_type == "CLASSIFIED_AS":
        source_label, target_label = records[0]["source_label"], "TaxonomyTerm"
    elif rel_type == "ACTIVE_ON":
        source_label, target_label = records[0]["source_label"], "Problem"
    elif rel_type == "AFFILIATED_WITH":
        source_label, target_label = "Person", "Institution"
    elif rel_type == "GENERALIZES":
        source_label, target_label = "Concept", "Concept"
    elif rel_type == "RELATED_TO":
        source_label, target_label = "Problem", "Problem"
    else:
        raise ValueError(f"Unsupported relationship type: {rel_type}")

    for batch in chunks(records, batch_size):
        rows = "[" + ", ".join(cypher_map(
            {k: v for k, v in row.items() if k not in {"target_label", "source_label"}}
        ) for row in batch) + "]"
        source_id = {
            "AUTHORED_BY": "paper_id", "APPEARED_AT": "paper_id",
            "IN_MODEL": "bound_id", "CLASSIFIED_AS": "source_node_id",
            "ACTIVE_ON": "source_node_id", "AFFILIATED_WITH": "person_id",
            "GENERALIZES": "source_node_id", "RELATED_TO": "source_node_id",
        }.get(rel_type, "problem_id")
        query = (f"UNWIND {rows} AS row "
                 f"MATCH (a:{source_label} {{id: row.{source_id}}}) "
                 f"MATCH (b:{target_label} {{id: row.target_id}}) "
                 f"MERGE (a)-[r:{rel_type}]->(b) "
                 "SET r += row")
        client.query(query)


def validate_paper_resume_ids(client, papers):
    """Read-only guard: planned canonical IDs must already exist under the same identity."""
    result = client.query_readonly(
        "MATCH (p:Paper) RETURN p.id AS id, p.citation_text AS citation_text"
    )
    existing = {row[0]: row[1] for row in result.records if row and row[0]}
    if not existing:
        return 0
    existing_identity = {
        node_id: paper_identity(parse_citation(citation_text or ""))
        for node_id, citation_text in existing.items()
    }
    plan_identity = {
        paper["id"]: paper_identity(paper)
        for paper in papers
    }
    for paper_id, identity in plan_identity.items():
        if paper_id not in existing:
            raise RuntimeError(f"Paper id {paper_id} is absent from non-empty graph; refusing resume")
        if existing_identity[paper_id] != identity:
            raise RuntimeError(f"Paper id {paper_id} resolves to a different citation identity")
    identity_counts = {}
    for identity in existing_identity.values():
        identity_counts[identity] = identity_counts.get(identity, 0) + 1
    existing_aliases = sum(count - 1 for count in identity_counts.values() if count > 1)
    return existing_aliases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path("build/source_catalog.json"))
    parser.add_argument("--url", default="http://localhost:8094")
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--load", action="store_true",
                        help="Actually write to Samyama. Without this flag, only validate and plan.")
    args = parser.parse_args()

    if args.batch_size < 1 or args.batch_size > 100:
        parser.error("--batch-size must be between 1 and 100")
    if args.load and urlsplit(args.url).port in {8092, 8093}:
        parser.error("live writes to protected ports 8092 and 8093 are prohibited")

    if not args.catalog.is_file():
        print(f"Catalog not found: {args.catalog}", file=sys.stderr)
        return 1

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    source = catalog.get("source", {})
    if source.get("actual_commit") != PINNED_COMMIT:
        print("Refusing to load: catalog is not from the pinned commit.")
        print("Expected:", PINNED_COMMIT)
        print("Found:", source.get("actual_commit"))
        return 1

    counts = catalog.get("counts", {})
    if counts.get("problem_pages") != 1053 or counts.get("topics") != 35:
        print("Refusing to load: catalog counts do not match the expected source.")
        print(json.dumps(counts, indent=2))
        return 1

    data = prepare(catalog)
    from etl.conformance import validate as validate_conformance
    errors = validate_conformance(data, raise_on_error=False)
    if errors:
        print(f"Refusing to load: {len(errors)} schema-conformance error(s).")
        for error in errors[:80]:
            print("ERROR:", error)
        return 1
    print("Schema conformance: PASS")
    print_plan(data)

    if not args.load:
        print("\nDRY RUN ONLY. No database writes performed.")
        print("Any later live write requires approval and a verified isolated target (default port 8094).")
        return 0

    client = SamyamaClient.connect(args.url)
    print("\nServer:", client.status())
    if client.ping() != "PONG":
        print("Refusing to load: server ping failed.")
        return 1

    # Check UNWIND/map syntax before starting the write phase.
    test = client.query_readonly(
        "UNWIND [{id: 'parser_preflight'}] AS row RETURN row.id AS id"
    )
    if not test.records:
        print("Cypher preflight returned no result; refusing to load.")
        return 1
    try:
        aliases = validate_paper_resume_ids(client, data["Paper"])
    except RuntimeError as exc:
        print(f"Refusing to resume: {exc}")
        return 1
    if aliases:
        print(f"Existing alternate Paper nodes for canonical works: {aliases}; retained without deletion.")

    print("\nCreating nodes...")
    from etl.conformance import load_spec
    labels = tuple(load_spec()["labels"])
    for label in labels:
        print(f"  {label}: {len(data[label]):,}")
        create_nodes(client, label, data[label], args.batch_size)

    print("\nCreating relationships...")
    relationships = tuple(load_spec()["relationships"])
    for rel_type in relationships:
        print(f"  {rel_type}: {len(data[rel_type]):,}")
        create_relationships(client, rel_type, data[rel_type], args.batch_size)

    final_status = client.status()
    print("\n=== Final server status ===")
    print(final_status)
    print("Planned node records:", sum(
        len(data[label]) for label in
        labels
    ))
    print("Planned relationship records:", sum(
        len(data[rel]) for rel in
        relationships
    ))

    print("PASS: load batches completed. MERGE makes repeated runs idempotent by node id and edge endpoints.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
