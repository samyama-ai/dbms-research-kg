"""Read-only audit of the seven ontology alignments in a persisted SQLite graph."""
from __future__ import annotations

import collections
import json
import sqlite3
from pathlib import Path

from etl.conformance import SPEC_PATH, load_spec, validate_ontology


def validate_sqlite_alignments(path: Path, *, spec_path: Path = SPEC_PATH) -> dict:
    """Audit ontology-alignment support in a persisted SQLite property graph.

    This reads only. The ontology mappings declared in schema/conformance.json are checked
    separately from the presence and quality of corresponding graph data.
    RDF instance triples are not expected by the documented LPG architecture.
    """
    spec = load_spec(spec_path)
    mapping = validate_ontology(spec_path)
    conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    try:
        metadata = dict(conn.execute("SELECT key,value FROM graph_metadata"))
        raw_labels = dict(conn.execute("SELECT label,count(*) FROM nodes GROUP BY label"))
        raw_rels = dict(conn.execute("SELECT rel_type,count(*) FROM edges GROUP BY rel_type"))
        labels = set(raw_labels)
        rels = set(raw_rels)
        expected_labels = set(spec["labels"])
        expected_rels = set(spec["relationships"])
        declared_labels = set(json.loads(metadata.get("schema_labels", "[]")))
        declared_rels = set(json.loads(metadata.get("schema_relationships", "[]")))
        declared_v1 = (metadata.get("graph_kind") == "catalog-schema-v1"
                       and declared_labels == expected_labels
                       and declared_rels == expected_rels)
        shape_errors = sorted((labels - expected_labels) | (rels - expected_rels)
                              | (expected_labels - declared_labels)
                              | (expected_rels - declared_rels))

        node_rows = [(label, json.loads(props)) for label, props in
                     conn.execute("SELECT label,properties_json FROM nodes")]
        edge_rows = [(rel, json.loads(props), src_label, dst_label)
                     for rel, props, src_label, dst_label in conn.execute(
                         "SELECT e.rel_type,e.properties_json,s.label,t.label "
                         "FROM edges e JOIN nodes s ON s.node_id=e.source_id "
                         "JOIN nodes t ON t.node_id=e.target_id")]
        missing_node_provenance = sum(
            field not in props or props[field] in (None, "")
            for _, props in node_rows for field in spec["provenance_required"])
        missing_edge_provenance = sum(
            field not in props or props[field] in (None, "")
            for _, props, _, _ in edge_rows
            for field in spec.get("relationship_provenance_required", []))
        missing_required_properties = collections.defaultdict(dict)
        for label in expected_labels:
            records = [props for kind, props in node_rows if kind == label]
            for prop in spec.get("node_properties", {}).get(label, {}).get("required", []):
                # Paper.title is conditional on a parsed citation, as specified
                # by the citation schema; uncertain raw citations may lack it.
                missing = sum(prop not in item or item[prop] in (None, "")
                              for item in records)
                if label == "Paper" and prop == "title":
                    missing = sum(item.get("parse_status") == "parsed"
                                  and not item.get("title") for item in records)
                missing_required_properties[label][prop] = missing
        missing_edge_properties = collections.defaultdict(dict)
        for rel in expected_rels:
            records = [props for kind, props, _, _ in edge_rows if kind == rel]
            for prop in spec.get("relationship_properties", {}).get(rel, {}).get("required", []):
                missing_edge_properties[rel][prop] = sum(
                    prop not in item or item[prop] in (None, "") for item in records)
        endpoint_errors = 0
        for rel, _, source_label, target_label in edge_rows:
            contract = spec["relationships"].get(rel)
            if contract is None:
                endpoint_errors += 1
                continue
            sources, targets = (set(contract[0].split("|")), set(contract[1].split("|")))
            endpoint_errors += int(source_label not in sources or target_label not in targets)

        def node_count(label, predicate):
            return sum(1 for kind, props in node_rows if kind == label and predicate(props))

        def edge_count(rel):
            return sum(1 for kind, _, _, _ in edge_rows if kind == rel)

        paper_count = raw_labels.get("Paper", 0)
        parsed_papers_without_title = node_count(
            "Paper", lambda p: p.get("parse_status") == "parsed" and not p.get("title"))
        terms = collections.defaultdict(set)
        for label, props in node_rows:
            if label == "TaxonomyTerm":
                terms[props.get("scheme")].add(props.get("code"))
        expected_terms = {
            "dbms-topic": {n.get("id") for label, n in node_rows
                           if label == "Topic"},
            "problem-type": set(spec["codes"]["Problem.problem_type"]),
            "solution-technique-family": set(spec["codes"]["Algorithm.family|System.family"]),
            "computation-model-workload": set(spec["codes"]["ComputationModel.class"]),
        }
        taxonomy_terms_valid = all(terms.get(scheme, set()) == values
                                   for scheme, values in expected_terms.items())
        cite_edges = [props for rel, props, _, _ in edge_rows if rel == "CITES"]
        missing_cito_role = sum(not props.get("role") for props in cite_edges)
        bad_cito_role = sum(props.get("role") not in spec["codes"]["CITES.role"]
                            for props in cite_edges if props.get("role"))
        cite_mapping_rows = [
            (json.loads(edge_props), json.loads(paper_props))
            for edge_props, paper_props in conn.execute(
                "SELECT e.properties_json,p.properties_json FROM edges e "
                "JOIN nodes p ON p.node_id=e.target_id "
                "WHERE e.rel_type='CITES' AND p.label='Paper'")
        ]
        artifact_map = {url.casefold().rstrip("/"): value for url, value in
                        spec.get("artifact_citation_mappings", {}).items()}
        bad_cito_mapping = 0
        for edge_props, paper_props in cite_mapping_rows:
            role = edge_props.get("role")
            expected = spec.get("cito_roles", {}).get(role, "cites")
            override = None
            if role == "artifact":
                override = artifact_map.get(str(paper_props.get("url", "")).casefold().rstrip("/"))
                if override:
                    expected = override["cito_property"]
                    if (edge_props.get("artifact_kind") != override["artifact_kind"]
                            or edge_props.get("cito_mapping_note") != override["note"]):
                        bad_cito_mapping += 1
                elif not edge_props.get("cito_mapping_note"):
                    bad_cito_mapping += 1
            if edge_props.get("cito_property") != expected:
                bad_cito_mapping += 1
        missing_author_positions = sum(
            rel == "AUTHORED_BY" and not props.get("position")
            for rel, props, _, _ in edge_rows)
        cito_role_counts = dict(collections.Counter(
            props.get("role", "<missing>") for props in cite_edges))
        related_evidence = collections.Counter(
            props.get("method", "<missing>") for rel, props, _, _ in edge_rows
            if rel == "RELATED_TO")
        affiliation_count = edge_count("AFFILIATED_WITH")
        required_property_errors = sum(
            count for fields in missing_required_properties.values()
            for count in fields.values())
        required_property_errors += sum(
            count for fields in missing_edge_properties.values() for count in fields.values())
        duplicate_logical_nodes = conn.execute(
            "SELECT count(*) FROM (SELECT label,logical_id FROM nodes "
            "GROUP BY label,logical_id HAVING count(*)>1)").fetchone()[0]
        duplicate_logical_edges = conn.execute(
            "SELECT count(*) FROM (SELECT rel_type,source_id,target_id FROM edges "
            "GROUP BY rel_type,source_id,target_id HAVING count(*)>1)").fetchone()[0]
        person_names_missing = node_count("Person", lambda p: not p.get("name"))
        institution_names_missing = node_count("Institution", lambda p: not p.get("name"))
        venue_names_missing = node_count("Venue", lambda p: not p.get("name"))
        title_missing = node_count("Paper", lambda p: not p.get("title"))
        id_missing = node_count("Paper", lambda p: not p.get("id"))
        relation_map = {
            "project_dbms_domain_ontology": (not shape_errors and not endpoint_errors
                                               and not required_property_errors
                                               and not duplicate_logical_nodes
                                               and not duplicate_logical_edges,
                                               {"expected_labels": sorted(expected_labels),
                                                "actual_labels": sorted(labels),
                                                "expected_relationships": sorted(expected_rels),
                                                "actual_relationships": sorted(rels),
                                                "declared_v1": declared_v1,
                                                "endpoint_errors": endpoint_errors,
                                                "required_property_errors": required_property_errors,
                                                "duplicate_logical_nodes": duplicate_logical_nodes,
                                                "duplicate_logical_relationships": duplicate_logical_edges}),
            "PROV-O": (not missing_node_provenance and not missing_edge_provenance,
                       {"missing_required_node_provenance_fields": missing_node_provenance,
                        "missing_required_edge_provenance_fields": missing_edge_provenance,
                        "snapshot_hash_references": conn.execute(
                            "SELECT count(*) FROM nodes WHERE origin='snapshot'").fetchone()[0]}),
            "SKOS": (taxonomy_terms_valid and edge_count("CLASSIFIED_AS") > 0,
                     {"taxonomy_terms_valid": taxonomy_terms_valid,
                      "taxonomy_term_count": raw_labels.get("TaxonomyTerm", 0),
                      "classification_edges": edge_count("CLASSIFIED_AS"),
                      "topic_count": raw_labels.get("Topic", 0),
                      "concept_count": raw_labels.get("Concept", 0),
                      "generalization_edges": edge_count("GENERALIZES"),
                      "missing_required_node_properties": dict(missing_required_properties),
                      "missing_required_edge_properties": dict(missing_edge_properties)}),
            "Dublin Core Terms": (not parsed_papers_without_title and edge_count("AUTHORED_BY") > 0
                                  and edge_count("IN_TOPIC") > 0,
                                  {"paper_nodes": paper_count,
                                   "papers_without_title": title_missing,
                                   "parsed_papers_without_title": parsed_papers_without_title,
                                   "creator_edges": edge_count("AUTHORED_BY"),
                                   "author_edges_missing_position": missing_author_positions,
                                   "subject_edges": edge_count("IN_TOPIC"),
                                   "relation_edges": edge_count("RELATED_TO")}),
            "FOAF": (not person_names_missing and not institution_names_missing,
                     {"person_nodes": raw_labels.get("Person", 0),
                      "people_missing_name": person_names_missing,
                      "institution_nodes": raw_labels.get("Institution", 0),
                      "institutions_missing_name": institution_names_missing}),
            "Schema.org": (not parsed_papers_without_title and not person_names_missing
                           and not venue_names_missing,
                           {"paper_ids_missing": id_missing,
                            "parsed_papers_without_title": parsed_papers_without_title,
                            "people_missing_name": person_names_missing,
                            "venues_missing_name": venue_names_missing}),
            "CiTO": (not missing_cito_role and not bad_cito_role and not bad_cito_mapping,
                     {"citation_edges": len(cite_edges),
                      "edges_missing_role": missing_cito_role,
                      "edges_with_invalid_role": bad_cito_role,
                      "role_counts": cito_role_counts,
                      "edges_with_invalid_cito_mapping": bad_cito_mapping,
                      "artifact_citation_mappings": len(artifact_map),
                      "unresolved_artifact_role_mapping": False}),
        }
        alignments = {}
        for name, (data_ok, evidence) in relation_map.items():
            if name == "project_dbms_domain_ontology" and (shape_errors or endpoint_errors):
                status = "FAIL"
            elif mapping["status"] == "FAIL":
                status = "FAIL"
            elif mapping["status"] == "NOT VERIFIED":
                status = "NOT VERIFIED"
            elif not data_ok:
                status = "PARTIAL"
            else:
                status = "PASS"
            alignments[name] = {
                "status": status,
                "mapping_status": mapping["status"],
                "sqlite_data_status": "PASS" if data_ok else "PARTIAL",
                "rdf_instance_serialization_required": False,
                "evidence": evidence,
            }
        return {
            "path": str(path.resolve()),
            "node_count": sum(raw_labels.values()),
            "edge_count": sum(raw_rels.values()),
            "node_counts": raw_labels,
            "edge_counts": raw_rels,
            "missing_required_node_properties": dict(missing_required_properties),
            "missing_required_relationship_properties": dict(missing_edge_properties),
            "author_edges_missing_position": missing_author_positions,
            "related_to_methods": dict(related_evidence),
            "affiliated_with_edges": affiliation_count,
            "ontology_mapping_validation": mapping,
            "alignments": alignments,
            "shape_errors": shape_errors,
            "endpoint_errors": endpoint_errors,
            "required_property_errors": required_property_errors,
            "duplicate_logical_nodes": duplicate_logical_nodes,
            "duplicate_logical_relationships": duplicate_logical_edges,
        }
    finally:
        conn.close()
