"""Institutions and affiliations named in §7 Current Research.

§7 names research groups in two shapes:

    "Suciu (UW)", "Stoica/Yang (Berkeley, Balsa)"     surname(s), then institution(s) in brackets
    "TUM (Neumann, Leis)", "EPFL DIAS (Ailamaki)"     institution, then surname(s) in brackets

A surname becomes an AFFILIATED_WITH link only when exactly one author cited on
the same page has that surname, so a bare "Wang" never picks an arbitrary Wang.
"""
from __future__ import annotations

import re

from etl.source_entities import institution_spans

PAREN = re.compile(r"\(([^()]{1,120})\)")
SURNAME = re.compile(r"[A-ZÀ-Ý][\w'’-]+")


def _surnames(text: str) -> list[str]:
    return [m.group(0) for m in SURNAME.finditer(text)]


def affiliation_mentions(item: str) -> list[tuple[str, str, str]]:
    """(surname, institution key, evidence) pairs stated in one §7 item."""
    spans = institution_spans(item)
    found = []
    for paren in PAREN.finditer(item):
        inside_start, inside_end = paren.start(1), paren.end(1)
        inside = [key for start, end, key in spans if start >= inside_start and end <= inside_end]
        before_text = item[max(0, paren.start() - 60):paren.start()]
        evidence = item[max(0, paren.start() - 60):paren.end()].strip()
        if inside:
            # "Suciu (UW)": the surnames right before the bracket, joined by / or &.
            lead = re.search(r"((?:[A-ZÀ-Ý][\w'’-]+)(?:\s*[/&]\s*[A-ZÀ-Ý][\w'’-]+)*)\s*$", before_text)
            if lead:
                for surname in re.split(r"\s*[/&]\s*", lead.group(1)):
                    found.extend((surname, key, evidence) for key in dict.fromkeys(inside))
            continue
        # "TUM (Neumann, Leis)": an institution ending just before the bracket.
        before = [key for start, end, key in spans
                  if end <= paren.start() and paren.start() - end <= 12]
        if before:
            key = before[-1]
            for surname in _surnames(paren.group(1)):
                found.append((surname, key, evidence))
    return found


def resolve_affiliations(item: str, page_authors: dict[str, list[tuple[str, str]]]):
    """(person key, author name, institution key, evidence) for unambiguous surnames.

    page_authors maps a folded surname to the (person key, name) of every author
    cited on the same page with that surname.
    """
    resolved = []
    for surname, institution, evidence in affiliation_mentions(item):
        candidates = page_authors.get(surname.casefold(), [])
        if len(candidates) == 1:
            person_key, name = candidates[0]
            resolved.append((person_key, name, institution, evidence))
    return resolved
