"""Named algorithms and systems from the bold text of §3 State of the Art.

The catalog writes each named method or system in bold inside §3, under a bullet
label such as **Theory-SOTA:** or **Systems-SOTA:**. This module turns those
bold mentions into Algorithm and System candidates and rejects the bold text
that is not a name: section labels, verdict words, citations ("Fagin (1983)"),
author lists ("Chandra–Merlin"), maths, and ordinary words that only start
with a capital because they open a phrase ("Adaptive", "Benchmarks").

Whether an ordinary dictionary word is a name is decided from the catalog
itself: a name such as "Calvin" or "Spanner" is (almost) never written in lower
case, while "adaptive" is. The decision is deterministic for a pinned catalog.
"""
from __future__ import annotations

import collections
import re
from pathlib import Path

WORDS_FILE = Path("/usr/share/dict/words")
BOLD = re.compile(r"\*\*([^*\n]{2,80})\*\*")
BULLET = re.compile(r"(?m)^\s*(?:[-*+]|\d+[.)])\s+")
LEADING_LABEL = re.compile(r"^\s*\*\*([^*\n]{1,60}?)\s*:?\s*\*\*\s*:?")
SECTION_LABEL = re.compile(
    r"^(?:theory|systems?|algorithmic|algorithms?|methods?|learning|formal|empirical|practice|"
    r"foundational|sota|survey|state of the art)(?:[- /](?:sota|empirical|practice|side|modeling|theory))*$",
    re.IGNORECASE)
VERDICT_WORDS = {
    "open", "closed", "not", "no", "yes", "none", "undecidable", "decidable", "np-hard",
    "np-complete", "conp-complete", "pspace-complete", "exptime-complete", "partially-solved",
    "partially solved", "empirically-open", "empirically open", "solved", "tight", "matching",
    "unknown", "best known", "lower bound", "upper bound", "theory", "systems", "benchmarks",
}
GENERIC = {
    "sql", "nosql", "newsql", "oltp", "olap", "htap", "acid", "api", "apis", "cpu", "cpus", "gpu", "gpus",
    "fpga", "fpgas", "ssd", "ssds", "nvm", "pmem", "rdma", "dram", "hdd", "nvme", "cxl", "simd", "avx",
    "avx-512", "ml", "ai", "llm", "llms", "dbms", "dbmss", "rdbms", "kv", "udf", "udfs", "io", "i/o", "etl",
    "json", "xml", "csv", "html", "http", "rpc", "tcp", "smt", "sat", "ilp", "lp", "bsp", "sdp", "tpc",
    "apache", "azure", "aws", "linux", "posix", "intel", "arm", "x86", "risc-v", "cuda", "opencl",
    "transformer", "transformers", "bert", "gpt", "lru", "fifo", "mru", "clock", "zipf", "zipfian",
}
STRUCTURE_SUFFIX = re.compile(
    r"(?:[- ](?:tree|trees|index|indexes|filter|filters|sketch|join|joins|sort|hash|hashing|heap|list|"
    r"trie|table|graph|cache|fifo|lru)|tree|trie)$", re.IGNORECASE)
COMPLEXITY_CLASS = re.compile(
    r"^(?:co-?|#|\d|N)*(?:P|NP|PTIME|EXPTIME|EXP|PSPACE|EXPSPACE|LOGSPACE|L|NL|NC|AC0|TC0|W\[\d\]|FPT|XP|APX|"
    r"PH|BPP|RP|ZPP|DP|UP|ELEMENTARY)(?:[- ](?:complete|hard|completeness|hardness|membership))?$", re.IGNORECASE)
NON_NAME_SUFFIX = re.compile(r"-(?:backed|based|style|like|aware|time|free|only|level|wise|driven)$", re.IGNORECASE)
SYSTEM_HINT = re.compile(
    r"(?:DB|SQL|Base|Store|Engine|Lake|House|Graph|Stream|KV|FS)\b|^Apache |^Azure |^AWS |^Google ")


def _load_words() -> frozenset[str]:
    try:
        return frozenset(w.strip().casefold() for w in WORDS_FILE.read_text(encoding="utf-8").split())
    except OSError:
        return frozenset()


def name_key(name: str) -> str:
    """Identity key: case-folded, dashes unified, spaces collapsed."""
    value = name.replace("–", "-").replace("—", "-").replace("‐", "-")
    return re.sub(r"\s+", " ", value).strip().casefold()


def _split(bold: str):
    if re.search(r"\b(?:19|20)\d\d\b", bold) or "et al" in bold:
        return                                           # a citation such as "Fagin (1983)"
    for part in re.split(r"\s*/\s*|\s*,\s*|\s*;\s*|\s+\+\s+|\s+and\s+|\s+vs\.?\s+", bold):
        part = part.strip(" .:;,\"'`*")
        part = re.sub(r"\s*\([^)]*$", "", part)          # an unclosed "(" and what follows
        part = re.sub(r"\s*\([^)]*\)\s*$", "", part)     # a trailing "(...)" gloss
        if part:
            yield part


def _bullets(text: str):
    """(context, bullet text) per bullet; context is 'systems', 'theory' or None."""
    pieces = BULLET.split(text)
    for piece in pieces:
        if not piece.strip():
            continue
        label = LEADING_LABEL.match(piece)
        context = None
        body = piece
        if label:
            words = label.group(1).casefold()
            if "system" in words or "engine" in words or "practice" in words or "empirical" in words:
                context = "systems"
            elif any(w in words for w in ("theory", "algorithm", "method", "formal", "learning", "foundational")):
                context = "theory"
            body = piece[label.end():]
        yield context, body


class NameOracle:
    """Decides, from the whole catalog, whether a capitalised dictionary word is used as a name."""

    def __init__(self, texts):
        self.words = _load_words()
        self.lower = collections.Counter()
        self.upper = collections.Counter()
        for text in texts:
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", text):
                tokens = re.findall(r"[A-Za-z][A-Za-z'’-]*", sentence)
                for i, token in enumerate(tokens):
                    key = token.casefold()
                    if token[0].islower():
                        self.lower[key] += 1
                    elif i > 0:
                        self.upper[key] += 1

    def is_name(self, candidate: str, *, reject: set[str], surnames: frozenset[str] = frozenset(),
                keep: frozenset[str] = frozenset()) -> bool:
        x = candidate.strip()
        if not x or len(x) > 40 or len(x.split()) > 4:
            return False
        key = name_key(x)
        if key in keep:
            return True
        if key in VERDICT_WORDS or key in GENERIC or key in reject or SECTION_LABEL.match(x):
            return False
        if len(x.replace(" ", "")) < 3 or NON_NAME_SUFFIX.search(x) or COMPLEXITY_CLASS.match(x):
            return False
        if re.search(r"['’]s$", x):
            return False                                  # "Reuter's": a possessive, not a name
        if "$" in x or "\\" in x or "=" in x or "⊑" in x or "≤" in x or "→" in x:
            return False
        if re.search(r"\b(?:19|20)\d\d\b", x) or "et al" in x:
            return False
        if not (x[0].isupper() or x[0].isdigit()):
            return False
        tokens = x.split()
        # Author lists "Chandra–Merlin", "Koutris–Wijsen": capitalised parts joined by en dashes.
        if "–" in x and all(part[:1].isupper() for part in re.split(r"–", x)):
            return False
        # Every further word must look like part of a name, not running text.
        for token in tokens[1:]:
            if not (token[:1].isupper() or token[:1].isdigit() or re.search(r".[A-Z]", token)
                    or re.fullmatch(r"[a-z]{1,3}", token) and token in {"of", "on", "for", "de", "la", "the"}):
                return False
        if re.search(r".[A-Z]", x.replace(" ", "")) or re.search(r"\d", x):
            return True                                   # CamelCase, acronym or digits: a name
        if len(tokens) == 1 and key in surnames:
            return False                                  # "Ullman", "Fagin": an author, not a system
        parts = [p.casefold() for p in re.split(r"[\s-]+", x) if p]
        if not all(p in self.words for p in parts):
            return True                                   # not ordinary English: a name
        if len(parts) > 1:
            return True                                   # Title Case phrase: "Join Order Benchmark"
        lower, upper = self.lower[parts[0]], self.upper[parts[0]]
        return upper >= 1 and lower <= upper // 2


def sota_mentions(text: str, oracle: NameOracle, *, reject: set[str],
                  surnames: frozenset[str] = frozenset(),
                  keep: frozenset[str] = frozenset()) -> list[tuple[str, str | None]]:
    """(name, context) for each bold name in §3 text, first occurrence order, no repeats."""
    seen, found = set(), []
    for context, body in _bullets(text):
        for bold in BOLD.findall(body):
            for part in _split(bold):
                key = name_key(part)
                if key in seen or not oracle.is_name(part, reject=reject, surnames=surnames, keep=keep):
                    continue
                seen.add(key)
                found.append((part, context))
    return found


def decide_labels(mentions_by_page, systems_allowlist) -> dict[str, str]:
    """name key -> 'System' or 'Algorithm', by the majority context across all pages."""
    allow = {name_key(s) for s in systems_allowlist}
    votes = collections.defaultdict(collections.Counter)
    first_name = {}
    for mentions in mentions_by_page:
        for name, context in mentions:
            votes[name_key(name)][context] += 1
            first_name.setdefault(name_key(name), name)
    labels = {}
    for key, vote in votes.items():
        systems, theory = vote["systems"], vote["theory"]
        if key in allow:
            labels[key] = "System"
        elif STRUCTURE_SUFFIX.search(first_name[key]):
            labels[key] = "Algorithm"            # data structures and algorithms: B^x-tree, S3-FIFO
        elif systems > theory:
            labels[key] = "System"
        elif theory > systems:
            labels[key] = "Algorithm"
        else:
            labels[key] = "System" if SYSTEM_HINT.search(first_name[key]) else "Algorithm"
    return labels
