"""Source-only schema validation for prepared graph records."""
from __future__ import annotations

import collections
import itertools
import json
import re
from datetime import date
from pathlib import Path

SPEC_PATH = Path(__file__).resolve().parents[1] / "schema" / "conformance.json"


class ConformanceError(ValueError):
    pass


def load_spec(path: Path = SPEC_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


PREFIXES = {
    "kg": "https://samyama.ai/kg/dbms-research/ontology#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "prov": "http://www.w3.org/ns/prov#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "dcterms": "http://purl.org/dc/terms/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "schema": "https://schema.org/",
    "cito": "http://purl.org/spar/cito/",
}
MAPPING_PREDICATES = {"rdfs:subClassOf", "rdfs:subPropertyOf", "rdfs:seeAlso",
                      "kg:mapsTo", "kg:mapsToScheme", "kg:mapsToCiTO"}


def validate_ontology(spec_path: Path = SPEC_PATH) -> dict:
    """Check the ontology mappings declared in schema/conformance.json.

    The project ships no RDF file: each label, relationship and property is mapped to the
    external vocabularies by the `ontology_mapping_triples` of the spec. Every mapping must use
    a known prefix and predicate, name a label, relationship or property of the schema as its
    subject, and every declared vocabulary must be used by at least one mapping.
    """
    spec = load_spec(spec_path)
    errors = []
    by_namespace = {uri: prefix for prefix, uri in PREFIXES.items()}
    used_prefixes = set()
    for name, alignment in spec["ontology_alignments"].items():
        if alignment.get("namespace") not in by_namespace:
            errors.append(f"alignment {name} has an unknown namespace {alignment.get('namespace')!r}")
    known_subjects = (set(spec["labels"]) | set(spec["relationships"])
                      | set(spec.get("ontology_datatype_properties", []))
                      | {"Topic", "Concept", "TaxonomyTerm"})
    for subject, predicate, obj in spec.get("ontology_mapping_triples", []):
        s_prefix, _, s_local = subject.partition(":")
        o_prefix, _, o_local = obj.partition(":")
        if s_prefix != "kg" or not (s_local in known_subjects or s_local.startswith("artifact-")):
            errors.append(f"mapping subject is not a schema term: {subject}")
        if predicate not in MAPPING_PREDICATES:
            errors.append(f"mapping predicate not allowed: {predicate}")
        if o_prefix not in PREFIXES or not o_local:
            errors.append(f"mapping object has an unknown prefix: {obj}")
        used_prefixes.add(o_prefix)
    for name, alignment in spec["ontology_alignments"].items():
        prefix = by_namespace.get(alignment.get("namespace"))
        if prefix and prefix != "kg" and prefix not in used_prefixes:
            errors.append(f"alignment {name} is declared but no mapping uses it")
    for role, term in spec.get("cito_roles", {}).items():
        if not re.fullmatch(r"[a-z][A-Za-z]+", str(term)):
            errors.append(f"CiTO role {role} maps to an invalid term {term!r}")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors,
            "mapping_count": len(spec.get("ontology_mapping_triples", []))}


def _errors(data: dict, spec: dict) -> list[str]:
    errors: list[str] = []
    labels = set(spec["labels"])
    relations = spec["relationships"]
    # Prepared graph data may include only populated labels/edges, while callers
    # explicitly supply an empty list to assert an implemented-but-empty type.
    missing_labels = labels - set(data)
    missing_rels = set(relations) - set(data)
    if missing_labels:
        errors.append(f"missing node collections: {sorted(missing_labels)}")
    if missing_rels:
        errors.append(f"missing relationship collections: {sorted(missing_rels)}")
    extra_labels = set(data) - labels - set(relations)
    if extra_labels:
        errors.append(f"unexpected graph collections: {sorted(extra_labels)}")

    node_index: dict[str, tuple[str, dict]] = {}
    for label in labels:
        seen: set[str] = set()
        for i, node in enumerate(data.get(label, [])):
            prefix = f"{label}[{i}]"
            node_id = node.get("id")
            if not isinstance(node_id, str) or not node_id:
                errors.append(f"{prefix}: id must be a non-empty string")
                continue
            if node_id in seen:
                errors.append(f"{prefix}: duplicate id {node_id}")
            seen.add(node_id)
            if node_id in node_index:
                errors.append(f"{prefix}: id {node_id} is not globally unique")
            node_index[node_id] = (label, node)
            for key in spec.get("node_properties", {}).get(label, {}).get("required", []):
                if key not in node or node[key] in (None, ""):
                    errors.append(f"{prefix}: missing required property {key}")
            for field in spec["provenance_required"]:
                if field not in node or node[field] in (None, ""):
                    errors.append(f"{prefix}: missing required provenance field {field}")
            allowed = spec["provenance_values"]
            for field, values in allowed.items():
                if node.get(field) not in values:
                    errors.append(f"{prefix}: invalid {field}={node.get(field)!r}")
            for field in ("retrieved_at", "source_date"):
                value = node.get(field)
                try:
                    parsed_date = date.fromisoformat(value)
                    if parsed_date.isoformat() != value:
                        raise ValueError(value)
                except (TypeError, ValueError):
                    errors.append(f"{prefix}: {field} must be ISO 8601 full date")
            if node.get("source") != "dbms_research":
                if not (label == "TaxonomyTerm" and node.get("source") == "project_schema"):
                    errors.append(f"{prefix}: source crosses the pinned source boundary")
            if label == "TaxonomyTerm" and node.get("provenance") != "schema-vocabulary":
                errors.append(f"{prefix}: taxonomy code node must be marked schema-vocabulary")
            if label != "TaxonomyTerm" and (node.get("source") == "project_schema"
                                            or node.get("provenance") == "schema-vocabulary"):
                errors.append(f"{prefix}: schema vocabulary provenance is only valid for TaxonomyTerm")
            if node.get("source_path"):
                if "5fff7f74508a52ac238f3bb608b8c8c872489fec" not in node.get("source_url", ""):
                    errors.append(f"{prefix}: page-derived node source_url is not pinned")
            for prop, allowed_values in spec["codes"].items():
                if "." not in prop:
                    continue
                for path in prop.split("|"):
                    if "." not in path:
                        continue
                    owner, key = path.split(".", 1)
                    if owner == label:
                        if key not in node:
                            errors.append(f"{prefix}: missing controlled property {key}")
                        elif node[key] not in allowed_values:
                            errors.append(f"{prefix}: {key}={node[key]!r} is outside controlled list")
            for prop, allowed_values in spec.get("property_values", {}).items():
                owner, key = prop.split(".", 1)
                if owner == label and node.get(key) not in allowed_values:
                    errors.append(f"{prefix}: {key}={node.get(key)!r} is outside controlled values")
            if label == "Paper" and node.get("year") is not None and not isinstance(node["year"], int):
                errors.append(f"{prefix}: Paper.year must be an integer")
            if label == "Paper" and node.get("doi"):
                if not re.fullmatch(r"10\.\d{4,9}/\S+", node["doi"]):
                    errors.append(f"{prefix}: DOI does not match ISO 26324 syntax")
            if label == "Paper" and node.get("parse_status") not in {"parsed", "uncertain"}:
                errors.append(f"{prefix}: invalid citation parse_status")
            if label == "Paper" and node.get("parse_status") == "parsed" and not node.get("title"):
                errors.append(f"{prefix}: parsed citation requires a title")
            if label == "Problem":
                for field in ("first_added", "last_reviewed", "last_substantive_update"):
                    value = node.get(field, "")
                    if value and not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value):
                        errors.append(f"{prefix}: {field} must be ISO 8601 YYYY-MM")
            if label in {"Paper", "Person", "Venue", "Concept", "Algorithm", "System", "ComputationModel"}:
                if not isinstance(node.get("page_count"), int) or node["page_count"] < 1:
                    errors.append(f"{prefix}: shared node requires positive page_count")
            if label == "TaxonomyTerm":
                schemes = spec["taxonomy_schemes"]
                if node.get("scheme") not in schemes or not node.get("code"):
                    errors.append(f"{prefix}: unknown taxonomy scheme or empty code")

    for label, pattern in spec["identifier_rules"].items():
        for i, node in enumerate(data.get(label, [])):
            if not re.fullmatch(pattern, node.get("id", "")):
                errors.append(f"{label}[{i}]: id violates stable identifier rule")

    for rel, (source_labels, target_labels) in relations.items():
        sources = set(source_labels.split("|"))
        targets = set(target_labels.split("|"))
        pairs = set()
        for i, edge in enumerate(data.get(rel, [])):
            prefix = f"{rel}[{i}]"
            edge_id = edge.get("id")
            if not isinstance(edge_id, str) or not edge_id:
                errors.append(f"{prefix}: id must be a non-empty string")
            for key in spec.get("relationship_properties", {}).get(rel, {}).get("required", []):
                if key not in edge or edge[key] in (None, ""):
                    errors.append(f"{prefix}: missing required relationship property {key}")
            for key in spec.get("relationship_provenance_required", []):
                if key not in edge or edge[key] in (None, ""):
                    errors.append(f"{prefix}: missing relationship provenance field {key}")
            if edge.get("source_commit") != spec["source_commit"]:
                errors.append(f"{prefix}: relationship source_commit is not pinned")
            source_id = (edge.get("source_node_id") or edge.get("problem_id")
                         or edge.get("paper_id") or edge.get("bound_id")
                         or edge.get("person_id") or edge.get("institution_id"))
            target_id = edge.get("target_id")
            if rel == "RESTS_ON":
                target_id = edge.get("target_id")
            source = node_index.get(source_id)
            target = node_index.get(target_id)
            if not source or source[0] not in sources:
                errors.append(f"{prefix}: source endpoint {source_id!r} must be {sorted(sources)}")
            if not target or target[0] not in targets:
                errors.append(f"{prefix}: target endpoint {target_id!r} must be {sorted(targets)}")
            pair = (source_id, target_id)
            if pair in pairs:
                errors.append(f"{prefix}: duplicate logical relationship endpoints {pair}")
            pairs.add(pair)
            if rel == "CITES" and edge.get("role") not in spec["codes"]["CITES.role"]:
                errors.append(f"{prefix}: invalid CITES.role {edge.get('role')!r}")
            if rel == "CITES":
                for key in ("verification_status", "role_status"):
                    allowed_values = spec["property_values"][f"CITES.{key}"]
                    if edge.get(key) not in allowed_values:
                        errors.append(f"{prefix}: invalid CITES {key}")
                target_node = node_index.get(target_id, (None, {}))[1]
                role = edge.get("role")
                expected_cito = spec.get("cito_roles", {}).get(role, "cites")
                if role == "artifact":
                    citation_url = str(target_node.get("url", "")).casefold().rstrip("/")
                    override = {url.casefold().rstrip("/"): value
                                for url, value in spec.get("artifact_citation_mappings", {}).items()}.get(citation_url)
                    if override:
                        expected_cito = override["cito_property"]
                        if edge.get("artifact_kind") != override["artifact_kind"]:
                            errors.append(f"{prefix}: artifact kind does not match cited source")
                        if edge.get("cito_mapping_note") != override["note"]:
                            errors.append(f"{prefix}: artifact mapping rationale does not match schema")
                    elif not edge.get("cito_mapping_note"):
                        errors.append(f"{prefix}: generic artifact fallback requires a mapping note")
                if edge.get("cito_property") != expected_cito:
                    errors.append(f"{prefix}: CITES cito_property must be {expected_cito!r}")
            if rel == "STATE_OF_ART" and edge.get("kind") not in spec["codes"]["STATE_OF_ART.kind"]:
                errors.append(f"{prefix}: invalid STATE_OF_ART.kind {edge.get('kind')!r}")
            if (rel == "CLASSIFIED_AS"
                    and edge.get("evidence_status") not in spec["codes"]["CLASSIFIED_AS.evidence_status"]):
                errors.append(f"{prefix}: invalid evidence_status")
            if rel == "CLASSIFIED_AS":
                term = target[1] if target else {}
                label = source[0] if source else ""
                expected_scheme = {"Problem": "problem-type", "Algorithm": "solution-technique-family",
                    "System": "solution-technique-family", "ComputationModel": "computation-model-workload"}.get(label)
                allowed = {
                    "problem-type": set(spec["codes"]["Problem.problem_type"]),
                    "solution-technique-family": set(spec["codes"]["Algorithm.family|System.family"]),
                    "computation-model-workload": set(spec["codes"]["ComputationModel.class"]),
                }
                topic_term = label == "Problem" and term.get("scheme") == "dbms-topic"
                if term.get("scheme") != expected_scheme and not topic_term:
                    errors.append(f"{prefix}: taxonomy scheme {term.get('scheme')!r} mismatches {label}")
                if term.get("scheme") in allowed and term.get("code") not in allowed[term["scheme"]]:
                    errors.append(f"{prefix}: taxonomy code is outside the scheme code list")
                if not edge.get("evidence"):
                    errors.append(f"{prefix}: classification evidence is required")
                if edge.get("evidence_status") == "source-explicit" and not edge.get("evidence"):
                    errors.append(f"{prefix}: source-explicit classification requires source evidence")
            if rel == "RELATED_TO":
                if edge.get("method") != "shared-papers-concepts":
                    errors.append(f"{prefix}: unsupported RELATED_TO method")
                if not isinstance(edge.get("score"), (int, float)) or not 0 < edge["score"] <= 1:
                    errors.append(f"{prefix}: RELATED_TO.score must be in (0, 1]")
                if edge.get("shared_evidence_count", 0) < 2:
                    errors.append(f"{prefix}: RELATED_TO needs at least two shared evidence items")
                if not edge.get("source_urls") or not edge.get("source_commit"):
                    errors.append(f"{prefix}: RELATED_TO requires evidence source URLs and commit")
    # The source catalog assigns every problem to exactly one topic. Validate
    # this invariant independently of the existence of individual endpoints.
    topic_degree: dict[str, int] = {}
    for edge in data.get("IN_TOPIC", []):
        source_id = edge.get("problem_id")
        topic_degree[source_id] = topic_degree.get(source_id, 0) + 1
    for node in data.get("Problem", []):
        if topic_degree.get(node.get("id"), 0) != 1:
            errors.append(f"Problem[{node.get('id')}]: must have exactly one IN_TOPIC edge")
    for label in ("Problem", "Algorithm", "System", "ComputationModel"):
        for node in data.get(label, []):
            expected_schemes = {"Problem": {"problem-type", "dbms-topic"},
                "Algorithm": {"solution-technique-family"}, "System": {"solution-technique-family"},
                "ComputationModel": {"computation-model-workload"}}[label]
            actual = {node_index.get(e.get("target_id"), (None, {}))[1].get("scheme")
                      for e in data.get("CLASSIFIED_AS", [])
                      if e.get("source_node_id") == node.get("id")}
            if not expected_schemes <= actual:
                errors.append(f"{label}[{node.get('id')}]: missing taxonomy membership "
                              f"{sorted(expected_schemes - actual)}")
            if label == "Problem":
                expected_codes = {"problem-type": node.get("problem_type"),
                                  "dbms-topic": node.get("topic_id")}
                expected_evidence = {
                    "problem-type": (node.get("topic_id") if node.get("problem_type_method") == "topic-crosswalk"
                                     else (node.get("title", "") + "\n" + node.get("problem_statement", "")).strip()),
                    "dbms-topic": node.get("topic_id"),
                }
                expected_status = {"problem-type": node.get("classification_evidence_status"),
                                   "dbms-topic": "source-explicit"}
            else:
                scheme = ("solution-technique-family" if label in {"Algorithm", "System"}
                          else "computation-model-workload")
                code_field = "family" if label in {"Algorithm", "System"} else "class"
                code = node.get(code_field)
                expected_codes = {scheme: code}
                expected_evidence = {scheme: node.get("family_evidence") or node.get("name")}
                expected_status = {scheme: "unresolved" if code == "unclassified" else "rule-based"}
            for edge in data.get("CLASSIFIED_AS", []):
                if edge.get("source_node_id") != node.get("id"):
                    continue
                term = node_index.get(edge.get("target_id"), (None, {}))[1]
                scheme = term.get("scheme")
                if scheme not in expected_codes:
                    continue
                if term.get("code") != expected_codes[scheme]:
                    errors.append(f"{label}[{node.get('id')}]: wrong {scheme} classification")
                if edge.get("evidence") != expected_evidence[scheme]:
                    errors.append(f"{label}[{node.get('id')}]: classification evidence does not match source field")
                if edge.get("evidence_status") != expected_status[scheme]:
                    errors.append(f"{label}[{node.get('id')}]: incorrect {scheme} evidence_status")
    terms_by_scheme: dict[str, set[str]] = collections.defaultdict(set)
    for node in data.get("TaxonomyTerm", []):
        terms_by_scheme[node.get("scheme")].add(node.get("code"))
    expected_terms = {
        "dbms-topic": {n.get("id") for n in data.get("Topic", [])},
        "problem-type": set(spec["codes"]["Problem.problem_type"]),
        "solution-technique-family": set(spec["codes"]["Algorithm.family|System.family"]),
        "computation-model-workload": set(spec["codes"]["ComputationModel.class"]),
    }
    for scheme, values in expected_terms.items():
        if terms_by_scheme.get(scheme, set()) != values:
            errors.append(f"taxonomy {scheme}: term membership mismatch; missing="
                          f"{sorted(values - terms_by_scheme.get(scheme, set()))}, extra="
                          f"{sorted(terms_by_scheme.get(scheme, set()) - values)}")

    # Recompute RELATED_TO from the catalog facts and enforce the documented
    # two-distinct-shared-evidence threshold, score, and source page links.
    evidence_by_problem = collections.defaultdict(set)
    for edge in data.get("CITES", []):
        evidence_by_problem[edge.get("problem_id")].add(("paper", edge.get("target_id")))
    for edge in data.get("RESTS_ON", []):
        evidence_by_problem[edge.get("problem_id")].add(("concept", edge.get("target_id")))
    evidence_to_problems = collections.defaultdict(set)
    for problem_id, items in evidence_by_problem.items():
        for item in items:
            evidence_to_problems[item].add(problem_id)
    expected_related = {}
    for item, problem_ids in evidence_to_problems.items():
        for left, right in itertools.combinations(sorted(problem_ids), 2):
            expected_related.setdefault((left, right), set()).add(item)
    expected_related = {pair: shared for pair, shared in expected_related.items()
                        if len(shared) >= 2 and any(kind == "paper" for kind, _ in shared)}
    actual_related = {}
    problem_records = {node.get("id"): node for node in data.get("Problem", [])}
    for edge in data.get("RELATED_TO", []):
        source_id, target_id = edge.get("problem_id"), edge.get("target_id")
        if not isinstance(source_id, str) or not isinstance(target_id, str):
            errors.append(f"RELATED_TO[{edge.get('id')}]: endpoints must be Problem IDs")
            continue
        pair = tuple(sorted((source_id, target_id)))
        if (source_id, target_id) != pair:
            errors.append(f"RELATED_TO[{edge.get('id')}]: direction must use deterministic endpoint order")
        shared = expected_related.get(pair)
        if not shared:
            errors.append(f"RELATED_TO[{edge.get('id')}]: pair lacks two shared source evidence items")
            continue
        actual_related[pair] = edge
        union = evidence_by_problem[pair[0]] | evidence_by_problem[pair[1]]
        papers = sum(kind == "paper" for kind, _ in shared)
        concepts = sum(kind == "concept" for kind, _ in shared)
        paths = sorted({problem_records[x].get("source_path") for x in pair})
        urls = [f"https://github.com/samyama-ai/dbms_research/blob/{spec['source_commit']}/{path}"
                for path in paths if path]
        if (edge.get("shared_evidence_count") != len(shared)
                or edge.get("shared_papers") != papers
                or edge.get("shared_concepts") != concepts
                or edge.get("score") != round(len(shared) / len(union), 6)
                or edge.get("source_urls") != urls):
            errors.append(f"RELATED_TO[{edge.get('id')}]: evidence counts, score, or source URLs do not recompute")
    if set(actual_related) != set(expected_related):
        errors.append(f"RELATED_TO coverage mismatch: missing={len(set(expected_related)-set(actual_related))}, "
                      f"extra={len(set(actual_related)-set(expected_related))}")
    return errors


def validate(data: dict, *, spec_path: Path = SPEC_PATH,
             raise_on_error: bool = True) -> list[str]:
    spec = load_spec(spec_path)
    errors = _errors(data, spec)
    if errors and raise_on_error:
        raise ConformanceError("Schema conformance failed:\n- " + "\n- ".join(errors))
    return errors

def validate_sqlite_alignments(path: Path, *, spec_path: Path = SPEC_PATH) -> dict:
    """Seven-alignment audit of a SQLite graph; implemented in etl/alignments.py."""
    from etl.alignments import validate_sqlite_alignments as audit
    return audit(path, spec_path=spec_path)


def summarize(data: dict) -> dict:
    spec = load_spec()
    return {
        "node_counts": {label: len(data.get(label, [])) for label in spec["labels"]},
        "relationship_counts": {rel: len(data.get(rel, [])) for rel in spec["relationships"]},
    }
