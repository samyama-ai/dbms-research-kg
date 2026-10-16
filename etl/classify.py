"""Rule-based code-list assignments, each returning the code and how it was decided.

The rules read only the pinned page text. They are deliberately simple and
documented in docs/standards.md, so a reviewer can check any assignment by
reading the sentence it came from.
"""
from __future__ import annotations

import re

from etl.source_entities import TOPIC_PROBLEM_TYPE

# --- Bound.kind -----------------------------------------------------------------
_IMPOSSIBLE = re.compile(
    r"impossib|cannot\b|can ?not be|undecidab|NP-hard|NP-complete|coNP|#P-hard|PSPACE|EXPTIME|W\[1\]|"
    r"\bhardness\b|-hard\b|inapproximab|no (?:polynomial|algorithm|protocol|scheme|deterministic)|"
    r"unless P ?= ?NP|\bFLP\b|\bCAP\b|\bSETH\b|\b3SUM\b|conditional lower bound")
_SPACE = re.compile(r"\bspace\b|\bbits\b|\bmemory\b|\bstorage\b|\bwords\b|footprint", re.IGNORECASE)
_TIME = re.compile(
    r"\$[^$]*(?:O|\\Theta|\\Omega|\\tilde\{O\})\s*\(|\btime\b|\blatency\b|\bthroughput\b|\brounds?\b|"
    r"\bI/Os?\b|\bsteps\b|\bcost\b|\bcomplexity\b|\bpolynomial\b|\blinear\b|\bquadratic\b|"
    r"\blogarithmic\b|\bpolylog", re.IGNORECASE)
_APPROX = re.compile(r"approximation ratio|\bapprox|\berror\b|\bq-error\b|\bguarantee|\bregret\b|"
                     r"\brecall\b|\baccuracy\b|\bprecision\b|\bcompetitive", re.IGNORECASE)


def bound_kind(text: str, direction: str = "upper") -> str:
    """time / space / impossibility / approximation / unclassified for one §4 or §5 text."""
    if direction == "lower" and _IMPOSSIBLE.search(text):
        return "impossibility"
    time, space = _TIME.search(text), _SPACE.search(text)
    if time and space:
        folded = text.casefold()
        time_weight = folded.count("time") + len(re.findall(r"O\(", text))
        return "time" if time_weight >= folded.count("space") else "space"
    if time:
        return "time"
    if space:
        return "space"
    if _IMPOSSIBLE.search(text):
        return "impossibility"
    if _APPROX.search(text):
        return "approximation"
    return "unclassified"


# --- Gap.verdict ------------------------------------------------------------------
_STATED = re.compile(
    r"^\s*\*\*\s*(open|genuinely open|wide open|partially[- ]solved|partially[- ]closed|"
    r"empirically[- ]open|closed|essentially closed|tight)\b", re.IGNORECASE)
_STATED_MAP = {"genuinely-open": "open", "wide-open": "open", "partially-closed": "partially-solved",
               "essentially-closed": "closed", "tight": "closed"}
_OPEN = re.compile(
    r"\b(?:remains? (?:wide |genuinely |largely )?open|(?:is|are|stays?|still) (?:genuinely |wide |largely |"
    r"completely |fundamentally |theoretically )?open|open (?:question|problem|gap|frontier|direction|case|part|"
    r"side)s?|(?:partially|theoretically|genuinely|wide) open|no (?:matching|tight|known|accepted|general|unified)|"
    r"unknown|unresolved|not (?:known|understood|settled)|what remains|remaining gaps?|leaving|"
    r"gap (?:remains|persists|is (?:wide|large|open|real|substantial|between))|far from|lacks?|missing|"
    r"no (?:proof|theory|model|characteri[sz]ation))\b", re.IGNORECASE)
_CLOSED = re.compile(
    r"\b(?:(?:is|are) (?:essentially |now |fully |asymptotically |largely |effectively )?(?:closed|tight|settled|"
    r"resolved)|bounds? (?:match|are tight|coincide)|matching (?:upper and lower )?bounds|tight (?:up to|bounds?)|"
    r"no (?:asymptotic )?(?:complexity )?gap|nearly closes|(?:gap|problem|question) is (?:essentially |now |largely )?"
    r"closed|closed (?:in theory|for|asymptotically))\b", re.IGNORECASE)
_PART = re.compile(
    r"\b(?:partially(?:-| )(?:solved|closed)|partly solved|closed for (?:restricted|special|some)|special cases?|"
    r"restricted (?:cases|classes|settings)|for (?:some|certain) (?:classes|cases))\b", re.IGNORECASE)
_EMPIRICAL = re.compile(
    r"\b(?:empirical(?:ly)? (?:open|gap|frontier|characteri[sz]ed)|largely empirical|fundamentally empirical|"
    r"gap is (?:\w+ )?empirical|(?:lacks?|no|without) (?:proven |formal |provable |theoretical )?guarantees|"
    r"works (?:well )?in practice|in practice but|no (?:formal|provable) (?:model|bound))\b", re.IGNORECASE)


def gap_verdict(text: str) -> tuple[str, str]:
    """(verdict, method) for §6. method is 'stated' (the page's own bold verdict), 'keyword' or 'none'.

    Keyword precedence: a closed phrase together with an open, partial or
    empirical phrase means only part is closed -> partially-solved.
    """
    stated = _STATED.match(text)
    if stated:
        word = stated.group(1).casefold().replace(" ", "-")
        return _STATED_MAP.get(word, word), "stated"
    plain = re.sub(r"[*_`]", "", text)
    if not plain.strip():
        return "unstated", "none"
    is_open, closed = bool(_OPEN.search(plain)), bool(_CLOSED.search(plain))
    partial, empirical = bool(_PART.search(plain)), bool(_EMPIRICAL.search(plain))
    if closed and (is_open or partial or empirical):
        return "partially-solved", "keyword"
    if closed:
        return "closed", "keyword"
    if partial:
        return "partially-solved", "keyword"
    if empirical:
        return "empirically-open", "keyword"
    if is_open:
        return "open", "keyword"
    return "unstated", "none"


# --- Problem.problem_type -----------------------------------------------------------
_PROBLEM_RULES = (
    ("query-optimization", (r"\b(query optimi[sz]ation|query optimi[sz]er|plan selection|join order(?:ing)?|"
                           r"cost model|cardinality estimat\w*)\b")),
    ("query-evaluation", (r"\b(query evaluation|query processing|join evaluation|query answering|"
                         r"conjunctive quer\w*|join algorithm\w*)\b")),
    ("data-modeling", r"\b(data model|schema design|normal form|dependenc(?:y|ies)|normali[sz]ation)\b"),
    ("data-integration", r"\b(data integration|data exchange|schema mapping|entity resolution|data cleaning)\b"),
    ("transaction-processing", (r"\b(transaction\w*|serializab\w*|concurrency control|isolation level\w*|"
                               r"recovery|logging)\b")),
    ("storage-indexing", r"\b(storage|indexing|index structure\w*|data layout|compression|buffer pool)\b"),
    ("distributed-data", r"\b(distributed|replication|sharding|consensus|partition\w*)\b"),
    ("analytics", r"\b(analytics|aggregation|machine learning|olap|approximate quer\w*)\b"),
    ("system-design", r"\b(database system|dbms architecture|self-driving|autonomous database|tuning)\b"),
)


def problem_type(title: str, statement: str, topic_id: str) -> tuple[str, str, str]:
    """(code, evidence_status, method). method: 'statement-rule', 'topic-crosswalk' or 'none'.

    The statement rule wins; when no rule fires, the page's own topic decides
    through the documented TOPIC_PROBLEM_TYPE crosswalk.
    """
    text = f"{title} {statement}".casefold()
    for code, pattern in _PROBLEM_RULES:
        if re.search(pattern, text):
            return code, "rule-based", "statement-rule"
    code = TOPIC_PROBLEM_TYPE.get((topic_id or "")[:2])
    if code:
        return code, "rule-based", "topic-crosswalk"
    return "unclassified", "unresolved", "none"


# --- Algorithm.family / System.family -------------------------------------------------
_FAMILY_RULES = (
    ("join-processing", r"join|triejoin|yannakakis|leapfrog|insideout|inside-out|generic|panda|free ?join|wcoj"),
    ("decomposition", r"gyo|decomposition|acyclic|hypertree|width"),
    ("query-optimization", (r"optimi[sz]er|cascades|volcano|bao|neo\b|balsa|lero|calcite|plan|cardinality|"
                           r"mscn|deepdb|naru|neurocard|bayescard|factorjoin|estimat")),
    ("indexing", (r"tree|index|hnsw|diskann|vamana|faiss|ivf|lsh|bloom|filter|trie|skiplist|skip list|"
                 r"hash|alex|pgm|lipp|rmi|masstree|art\b|learned")),
    ("transaction-processing", (r"mvcc|2pl|occ|silo|hekaton|calvin|tictoc|cicada|aria|polyjuice|transaction|"
                               r"lock|commit|serializ|isolation|snapshot")),
    ("distributed-processing", (r"paxos|raft|zab|pbft|bft|hotstuff|consensus|spanner|percolator|"
                               r"spark|flink|trino|presto|mapreduce|hadoop|dask|ray\b|crdt|gossip|replica")),
    ("streaming-system", r"stream|kafka|flink|millwheel|naiad|timely|trill|storm|beam|window|watermark"),
    ("storage", (r"lsm|rocksdb|leveldb|wal|aries|log|buffer|cache|ssd|nvm|pmem|compression|compaction|"
                r"parquet|orc|arrow|btrblocks|fastlanes|gorilla|chimp|elf|storage|file ?system|object store")),
    ("analytics", (r"sketch|hyperloglog|count-?min|sampl|histogram|aqp|verdictdb|blinkdb|olap|cube|"
                  r"approximate|provenance|clean|holoclean|dedup|entity|privacy|dp\b")),
    ("analytical-dbms", (r"duckdb|umbra|hyper\b|monetdb|bigquery|snowflake|redshift|clickhouse|vertica|"
                        r"vectorwise|druid|pinot|photon|velox|datafusion|hana")),
    ("relational-dbms", (r"mysql|postgres|sqlite|mariadb|cockroach|tidb|yugabyte|oracle|sql server|db2|"
                        r"aurora|socrates|neon|polardb|foundationdb")),
    ("query-engine", r"engine|executor|vectori[sz]|compil|jit|morsel"),
)


def technique_family(name: str, label: str) -> str:
    """Family code for an Algorithm or System name; 'unclassified' when no rule fires."""
    folded = name.casefold()
    order = _FAMILY_RULES
    if label == "System":   # product names first for systems
        order = tuple(r for r in _FAMILY_RULES if r[0] in {"analytical-dbms", "relational-dbms",
                                                           "streaming-system", "distributed-processing"}) + \
            tuple(r for r in _FAMILY_RULES if r[0] not in {"analytical-dbms", "relational-dbms",
                                                           "streaming-system", "distributed-processing"})
    for code, pattern in order:
        if re.search(pattern, folded):
            return code
    return "unclassified"
