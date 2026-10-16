"""Load the validated DBMS Research catalog into an isolated Samyama instance."""
from __future__ import annotations

import re

from etl.citations import paper_identity, parse_citation, person_key
from etl.classify import bound_kind, gap_verdict, problem_type, technique_family
from etl.engine_load import (  # noqa: F401  (re-exported)
    create_nodes,
    create_relationships,
    main,
    print_plan,
    validate_paper_resume_ids,
)
from etl.finalize import finalize
from etl.records import (  # noqa: F401  (re-exported)
    PINNED_COMMIT,
    annotate_provenance,
    chunks,
    classification_evidence,
    cypher_literal,
    cypher_map,
    cypher_string,
    person_name_form,
    stable_id,
    unique_records,
)
from etl.research_links import resolve_affiliations
from etl.sota_entities import NameOracle, decide_labels, name_key, sota_mentions
from etl.source_entities import (
    ALGORITHMS,
    CONCEPTS,
    CONFERENCE_VENUES,
    INSTITUTIONS,
    SYSTEMS,
    matching_concepts,
    matching_institutions,
    matching_models,
    matching_terms,
    model_class_code,
    venue_kind_code,
)


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
    page_authors = {}
    for source_problem in catalog["problems"]:
        by_surname = page_authors.setdefault(source_problem["id"], {})
        for raw_ref in source_problem.get("reference_entries", []):
            parsed_author = parse_citation(raw_ref, bool(source_problem.get("metadata", {}).get("refs_unverified")))
            for author_name in parsed_author["authors"]:
                author_candidates.setdefault(person_key(author_name), author_name)
                key = person_key(author_name)
                if key.split():
                    entry = (key, author_candidates[key])
                    if entry not in by_surname.setdefault(key.split()[-1], []):
                        by_surname[key.split()[-1]].append(entry)
    authors_by_surname = {}
    for author_key, author_name in author_candidates.items():
        surname = author_key.split()[-1] if author_key.split() else ""
        authors_by_surname.setdefault(surname, []).append((author_key, author_name))

    # Named algorithms/systems in §3 bold text (etl/sota_entities.py). Words that
    # are concepts, institutions, venues or cited authors' surnames are not names.
    oracle = NameOracle(text for p in catalog["problems"] for text in p["sections"].values())
    not_names = ({name_key(alias) for concept, aliases in CONCEPTS.items() for alias in (concept, *aliases)}
                 | {name_key(name) for _, name, _, _ in INSTITUTIONS} | {key for key, *_ in INSTITUTIONS}
                 | {venue.casefold() for venue in CONFERENCE_VENUES})
    surnames = frozenset(authors_by_surname)
    keep_names = frozenset(name_key(x) for x in (*SYSTEMS, *ALGORITHMS))
    sota_by_page = {p["id"]: sota_mentions(p["sections"].get("state_of_the_art", ""), oracle,
                                           reject=not_names, surnames=surnames, keep=keep_names)
                    for p in catalog["problems"]}
    sota_labels = decide_labels(sota_by_page.values(), SYSTEMS)
    for name in ALGORITHMS:
        sota_labels[name_key(name)] = "Algorithm"
    for name in SYSTEMS:
        sota_labels[name_key(name)] = "System"
    institutions_by_id = {}
    affiliations = {}

    for problem in catalog["problems"]:
        meta = problem["metadata"]
        sections = problem["sections"]
        pid = problem["id"]

        ptype, ptype_status, ptype_method = problem_type(
            problem["title"], sections.get("problem_statement", ""), problem["topic_id"])
        problems.append({
            "id": pid,
            "slug": pid.rsplit("/", 1)[-1],
            "title": problem["title"],
            "status": problem["status"],
            "problem_type": ptype,
            "classification_evidence_status": ptype_status,
            "problem_type_method": ptype_method,
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
                "kind": bound_kind(text, kind),
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
            page_url = f"https://github.com/samyama-ai/dbms_research/blob/{PINNED_COMMIT}/{problem['source_path']}"
            for inst_key, inst_name, inst_kind in matching_institutions(item):
                iid = f"institution:{inst_key}"
                institutions_by_id.setdefault(iid, {"id": iid, "name": inst_name, "kind": inst_kind,
                    "source_path": problem["source_path"], "extraction": "listed_institution_in_section_7"})
                active_edges.append({"source_node_id": iid, "source_label": "Institution",
                    "target_id": pid, "problem_id": pid, "direction": item, "source_url": page_url})
            for person_key_value, author_name, inst_key, evidence in resolve_affiliations(
                    item, page_authors.get(pid, {})):
                person_id = stable_id("person", person_key_value)
                iid = f"institution:{inst_key}"
                people_by_id.setdefault(person_id, {"id": person_id, "name": author_name,
                    "name_form": person_name_form(author_name), "source_path": problem["source_path"]})
                affiliations.setdefault((person_id, iid), {"id": f"{person_id}->{iid}",
                    "person_id": person_id, "target_id": iid, "evidence": evidence,
                    "source_url": page_url, "method": "parsed"})

        for concept in matching_concepts(sections.get("mathematical_foundations", "")):
            cid = stable_id("concept", concept.casefold())
            concepts_by_id.setdefault(cid, {"id": cid, "name": concept,
                "source_path": problem["source_path"], "extraction": "allowlisted_source_phrase"})
            rests_on_edges.append({"problem_id": pid, "concept_id": cid})

        sota_text = sections.get("state_of_the_art", "")
        mentions = [(name, None) for name in matching_terms(sota_text, list(SYSTEMS) + list(ALGORITHMS))]
        mentions += sota_by_page.get(pid, [])
        seen_targets = set()
        for name, context in mentions:
            key = name_key(name)
            label = sota_labels.get(key, "Algorithm")
            prefix = "system" if label == "System" else "algorithm"
            target_id = stable_id(prefix, key)
            if target_id in seen_targets:
                continue
            seen_targets.add(target_id)
            extraction = ("allowlisted_source_phrase" if key in keep_names
                          else "bold_name_in_section_3")
            record = {"id": target_id, "name": name, "family": technique_family(name, label),
                      "source_path": problem["source_path"], "extraction": extraction}
            if label == "System":
                record["kind"] = "named-system"
                systems_by_id.setdefault(target_id, record)
            else:
                algorithms_by_id.setdefault(target_id, record)
            edge_kind = context or ("systems" if label == "System" else "theory")
            sota_edges.append({"problem_id": pid, "target_id": target_id, "kind": edge_kind,
                               "target_label": label})

        for kind in ("upper", "lower"):
            for model in matching_models(sections.get(f"{kind}_bound", "")):
                mid = stable_id("model", model.casefold())
                models_by_id.setdefault(mid, {"id": mid, "name": model,
                    "class": model_class_code(model),
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
                    "name": parsed["venue_raw"], "kind": venue_kind_code(parsed["venue_raw"]),
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
        "Institution": list(institutions_by_id.values()),
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
        "AFFILIATED_WITH": list(affiliations.values()),
        "GENERALIZES": [],
        "RELATED_TO": [],
        "FROM_SOURCE": unique_records([{"id": f"{p['id']}->datasource:dbms_research",
            "problem_id": p["id"], "target_id": "datasource:dbms_research"} for p in problems]),
        "CLASSIFIED_AS": [],
    }

    return finalize(data, source)


if __name__ == "__main__":
    raise SystemExit(main())
