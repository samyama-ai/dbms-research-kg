"""Conservative parsing of citation lines from the pinned source catalog."""
from __future__ import annotations

import re
import unicodedata

DOI_URL = re.compile(r"https?://(?:dx\.)?doi\.org/(10\.\d{4,9}/[^\s\]]+)", re.IGNORECASE)
DOI = re.compile(r"\b(10\.\d{4,9}/[^\s\]]+)", re.IGNORECASE)
URL = re.compile(r"https?://[^\s)\]]+", re.IGNORECASE)
ARXIV_URL = re.compile(r"https?://(?:www\.)?arxiv\.org/(?:abs|pdf)/([^?#)\s]+)", re.IGNORECASE)
DBLP_RECORD_URL = re.compile(r"https?://(?:www\.)?dblp\.org/rec/([^?#)\s]+)", re.IGNORECASE)
YEAR = re.compile(r"\b((?:18|19|20)\d{2})(?:\s*/\s*((?:18|19|20)\d{2}))?\b")
TITLE = re.compile(r"\*\*(.+?)\*\*|\*(.+?)\*|“([^”]+)”|\"([^\"]+)\"")
ROLE_CODES = {"foundational", "sota", "survey", "systems", "docs", "artifact", "attack"}


def normalize_role(raw: str) -> tuple[str, str]:
    """Normalize source tags without converting unsupported tags into known roles."""
    parts = [re.sub(r"\s+", "-", x.strip().casefold()) for x in re.split(r"[/,]", raw) if x.strip()]
    normalized = []
    for part in parts:
        part = {"lower-bound": "unclassified", "lower-bounds": "unclassified"}.get(part, part)
        if part in ROLE_CODES and part not in normalized:
            normalized.append(part)
        elif part != "unclassified":
            return "unclassified", "unresolved"
    if len(normalized) == 1 and len(parts) == 1:
        return normalized[0], "source-explicit"
    if len(normalized) > 1:
        return "mixed", "source-explicit"
    return "unclassified", "unresolved"


def parse_citation(raw: str, page_unverified: bool = False) -> dict:
    """Return conservative metadata and retain raw text for every citation.

    A citation is ``parsed`` only when an explicit title delimiter exists. Authors
    are emitted only when text before that title has a clear terminal period.
    Venue/year are emitted only when a year follows an explicit title.
    """
    raw_text = raw
    text = " ".join(raw.split())
    doi_match = DOI_URL.search(text) or DOI.search(text)
    role_match = re.search(r"\*\*\[([^\]]+)\]\*\*", text)
    role, role_status = normalize_role(role_match.group(1) if role_match else "")
    doi = clean_doi(doi_match.group(1)) if doi_match else None
    urls = URL.findall(text)
    url = urls[0].rstrip(".,;") if urls else None
    arxiv_match = ARXIV_URL.search(text)
    dblp_match = DBLP_RECORD_URL.search(text)
    title_match = next((m for m in TITLE.finditer(text)
                        if not next(g for g in m.groups() if g is not None).strip().startswith("[")), None)
    year_matches = list(YEAR.finditer(text))
    title = None
    authors, authors_raw, venue, year = [], "", None, None
    confident = bool(title_match)
    if title_match:
        title = next(group for group in title_match.groups() if group is not None).strip()
        author_part = text[:title_match.start()].strip()
        author_part = re.sub(r"^\s*[-*+]?\s*\*{0,2}\[[^\]]+\]\*{0,2}\s*", "", author_part)
        author_part = author_part.strip(" -*.\t")
        authors_raw = author_part
        authors = parse_authors(author_part)
        following = text[title_match.end():]
        ym = YEAR.search(following)
        if ym:
            year = int(ym.group(1))
            venue_text = following[:ym.start()].strip(" .,;—–-")
            venue_text = re.sub(r"\s*[—–-]\s*\[.*$", "", venue_text).strip()
            if venue_text and len(venue_text) <= 100:
                venue = venue_text
    else:
        confident = False
    year_values = [int(m.group(1)) for m in year_matches]
    if len(set(year_values)) > 1:
        year = None
        confident = False
    return {
        "citation_text": raw_text,
        "citation_normalized": text,
        "title": title or "",
        "authors": authors,
        "authors_raw": authors_raw,
        "venue_raw": venue or "",
        "year": year,
        "doi": doi or "",
        "arxiv_id": arxiv_match.group(1).removesuffix(".pdf") if arxiv_match else "",
        "dblp_key": dblp_match.group(1).removesuffix(".html") if dblp_match else "",
        "url": url or "",
        "parse_status": "parsed" if confident else "uncertain",
        # Only a reference whose own text says "unverified" is unverified. The page
        # header refs_unverified is a count and rarely says which reference it means.
        "verification_status": "unverified" if re.search(r"\bunverified\b", raw, re.IGNORECASE) else "source_only",
        "source_verified": False,
        "role_raw": role_match.group(1) if role_match else "",
        "role": role,
        "role_status": role_status,
    }


def person_key(name: str) -> str:
    normalized = unicodedata.normalize("NFKC", name).casefold().strip()
    # Canonicalize "Surname, A.B." to the same key as "A. B. Surname".
    if "," in normalized:
        surname, initials = normalized.split(",", 1)
        letters = re.findall(r"[a-z]", initials)
        if letters and re.fullmatch(r"[\s.,-]*", re.sub(r"[a-z]", "", initials)):
            normalized = " ".join(letters + [surname])
    normalized = re.sub(r"[^\w]+", " ", normalized, flags=re.UNICODE)
    return " ".join(normalized.split())


def normalize_title(title: str) -> str:
    value = unicodedata.normalize("NFKC", title).casefold()
    value = re.sub(r"[*_`]+", "", value)
    value = re.sub(r"[^\w]+", " ", value, flags=re.UNICODE)
    return " ".join(value.split())


def clean_doi(value: str) -> str:
    """Remove citation punctuation while preserving balanced DOI parentheses."""
    value = value.strip()
    while value and value[-1] in ".,;:":
        value = value[:-1]
    while value.endswith(")") and value.count(")") > value.count("("):
        value = value[:-1]
    return value


def paper_identity(parsed: dict) -> str:
    """Build a stable identity from explicit identifiers, then safe fallbacks.

    Explicit, different DOIs remain distinct even when arXiv IDs match.
    Existing graph IDs and citation occurrences are handled separately.
    """
    doi = clean_doi(str(parsed.get("doi") or "")).casefold()
    if doi:
        return "doi:" + doi

    arxiv_id = str(parsed.get("arxiv_id") or "").strip().casefold()
    arxiv_id = re.sub(r"v\d+$", "", arxiv_id)
    if arxiv_id:
        return "arxiv:" + arxiv_id

    dblp_key = str(parsed.get("dblp_key") or "").strip().casefold()
    if dblp_key:
        return "dblp:" + dblp_key.removesuffix(".html")

    title = normalize_title(parsed.get("title", ""))
    if title:
        return f"title:{title}|year:{parsed.get('year') or ''}"
    raw = parsed.get("citation_normalized", parsed.get("citation_text", ""))
    return "raw:" + " ".join(raw.casefold().split())


def _strong_ids(parsed: dict) -> dict[str, str]:
    """The explicit identifiers of one citation, normalised as in paper_identity."""
    ids = {"doi": clean_doi(str(parsed.get("doi") or "")).casefold(),
           "arxiv": re.sub(r"v\d+$", "", str(parsed.get("arxiv_id") or "").strip().casefold()),
           "dblp": str(parsed.get("dblp_key") or "").strip().casefold().removesuffix(".html")}
    return {kind: value for kind, value in ids.items() if value}


def merge_identities(records: list[dict]) -> list[int]:
    """For each citation, the index of the citation that represents its paper.

    Citations are the same paper when they share an explicit identifier (DOI,
    arXiv id without version, DBLP key), or share normalised title and year
    while their identifiers do not conflict: two different DOIs stay two works
    (a conference paper and its journal version). The representative is the
    citation with the most identifiers, earliest in catalog order on ties, so
    a paper's DOI always occurs in its own citation text.
    """
    parent = list(range(len(records)))
    strong = [_strong_ids(r) for r in records]
    merged = [dict(s) for s in strong]          # identifiers of each group, kept at its root

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j, *, check_conflict):
        a, b = find(i), find(j)
        if a == b:
            return
        if check_conflict and any(merged[a].get(k) not in (None, v) for k, v in merged[b].items()):
            return
        if b < a:
            a, b = b, a
        parent[b] = a
        for kind, value in merged[b].items():
            merged[a].setdefault(kind, value)

    first_by_id = {}
    for i, ids in enumerate(strong):
        for kind, value in ids.items():
            j = first_by_id.setdefault((kind, value), i)
            if j != i:
                union(j, i, check_conflict=True)
    first_by_title = {}
    for i, record in enumerate(records):
        title, year = normalize_title(record.get("title", "")), record.get("year")
        if title and year:
            j = first_by_title.setdefault((title, year), i)
            if j != i:
                union(j, i, check_conflict=True)
    best = {}
    for i in range(len(records)):
        root = find(i)
        if root not in best or len(strong[i]) > len(strong[best[root]]):
            best[root] = i
    return [best[find(i)] for i in range(len(records))]


def parse_authors(value: str) -> list[str]:
    """Parse only clearly delimited author lists, dropping et-al placeholders."""
    value = value.strip()
    if not value:
        return []
    # Format: Surname, initials, Surname, initials.
    tokens = [x.strip() for x in re.split(r",\s*", value) if x.strip()]
    grouped = []
    i = 0
    while i < len(tokens):
        current = tokens[i]
        if i + 1 < len(tokens) and re.fullmatch(r"(?:[A-Z]\.\s*)+", tokens[i + 1], re.IGNORECASE):
            current = current.rstrip(" .") + ", " + tokens[i + 1].strip()
            i += 1
        grouped.append(current)
        i += 1
    authors = []
    for candidate in grouped:
        candidate = re.sub(r"^\*+", "", candidate).strip()
        if candidate.casefold().strip(" .") in {"et al", "and others", "others"}:
            continue
        if re.fullmatch(r"[A-Z]\.??", candidate):
            continue
        # Reject role tags and non-name prose. Bare surnames and initials+surnames
        # are accepted because they are explicitly listed in the citation source.
        if re.fullmatch(r"[A-Z][A-Za-z'’.-]*(?:\s+[A-Z][A-Za-z'’.-]*)*(?:,\s*(?:[A-Z]\.\s*)+[A-Z]?\.?)?", candidate):
            authors.append(candidate)
    return authors
