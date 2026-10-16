"""Shared helpers for building graph records (ids, de-duplication, code rules, provenance)."""
from __future__ import annotations

import hashlib
import re

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
