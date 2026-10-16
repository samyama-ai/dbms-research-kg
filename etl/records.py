"""Shared helpers for building graph records (ids, de-duplication, provenance)."""
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
    """A Cypher map literal. A missing value (None) is left out, so the property is absent and
    reads as null; writing it as '' made 364 paper years an empty string on the engine."""
    return "{" + ", ".join(
        f"{key}: {cypher_literal(value)}"
        for key, value in record.items() if value is not None
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


def person_name_form(name):
    value = name.strip()
    if re.fullmatch(r"(?:[A-Z]\.\s*)+", value):
        return "initials"
    if re.fullmatch(r"(?:[A-Z]\.\s*)+[A-Z][A-Za-z'’\-]+", value):
        return "initials"
    if len(value.split()) == 1:
        return "surname"
    return "full"


def classification_evidence(problem):
    statement = (problem.get("sections", {}).get("problem_statement")
                 or problem.get("problem_statement", ""))
    return "\n".join((problem.get("title", ""),
                      statement)).strip()


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
