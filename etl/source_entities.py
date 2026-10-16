"""Small, reviewable source-term lists for high-confidence entity extraction."""
from __future__ import annotations

import re

CONCEPTS = {
    "AGM bound": ("AGM bound", "Atserias-Grohe-Marx bound", "fractional edge cover bound"),
    "acyclicity": ("α-acyclicity", "alpha-acyclicity", "β-acyclicity", "gamma-acyclicity"),
    "conjunctive query": ("conjunctive queries", "conjunctive query"),
    "fractional hypertree width": ("fractional hypertree width",),
    "functional dependency": ("functional dependencies", "functional dependency"),
    "hypergraph": ("hypergraphs", "hypergraph"),
    "hypertree width": ("hypertree width",),
    "join tree": ("join trees", "join tree"),
    "treewidth": ("treewidth",),
    "data provenance": ("provenance semirings", "data provenance"),
}

SYSTEMS = (
    "BigQuery", "CockroachDB", "DuckDB", "HyPer", "LogicBlox", "MariaDB",
    "MonetDB", "MySQL", "PostgreSQL", "Presto", "Redshift", "Snowflake",
    "Spark SQL", "SQLite", "TiDB", "Trino", "Umbra",
)

ALGORITHMS = (
    "GYO reduction", "Leapfrog Triejoin", "Generic Join", "InsideOut algorithm",
    "Yannakakis algorithm", "maximum-cardinality search",
)

MODELS = {
    "word-RAM": (r"\bword[- ]RAM\b",),
    "cell-probe": (r"\bcell[- ]probe\b",),
    "external-memory": (r"\bexternal[- ]memory(?: model)?\b",),
    "comparison": (r"\bcomparison[- ]based model\b", r"\bcomparison model\b"),
    "streaming": (r"\bstreaming model\b",),
    "I/O": (r"\bI/O model\b", r"\bexternal-memory I/Os\b"),
    "PRAM": (r"\bPRAM\b", r"\bparallel RAM\b"),
    "Turing machine": (r"\bTuring machine model\b",),
}


def matching_terms(text: str, terms: tuple[str, ...] | list[str]) -> list[str]:
    found = []
    folded = text.casefold()
    for term in terms:
        needle = re.escape(term.casefold()).replace(r"\ ", r"\s+")
        if re.search(r"(?<!\w)" + needle + r"(?!\w)", folded):
            found.append(term)
    return found


def matching_concepts(text: str) -> list[str]:
    folded = text.casefold()
    found = []
    for concept, aliases in CONCEPTS.items():
        if any(re.search(r"(?<!\w)" + re.escape(alias.casefold()) + r"(?!\w)", folded)
               for alias in aliases):
            found.append(concept)
    return found


def matching_models(text: str) -> list[str]:
    return [model for model, patterns in MODELS.items()
            if any(re.search(pattern, text, re.I) for pattern in patterns)]
