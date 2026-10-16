# Standards

The external standards this graph follows, and how each is checked.

The seven vocabulary alignments (project ontology, PROV-O, SKOS, Dublin Core, FOAF, Schema.org,
CiTO) are in [`ontology.md`](ontology.md#alignment-with-other-vocabularies). The four taxonomies and
twelve code lists are in [`taxonomy.md`](taxonomy.md). All three are declared in
[`schema/conformance.json`](../schema/conformance.json) and enforced by `etl.conformance.validate`.

## Standards and specification groups (6)

`python -m etl.audit` checks each group item by item against the built graph
([audit report](audit-report.md)).

| Group | Conformance rule |
|---|---|
| PROV-O | Every node has `source`, `provenance`, `method` and the lock-derived `retrieved_at` and `source_date`; page-derived nodes have a commit-pinned `source_url`; `FROM_SOURCE` points at the pinned DataSource. A field and edge mapping, not a full PROV-O serialisation. |
| SKOS | Taxonomy terms carry `scheme` and `notation`; the topic scheme stays flat; only the listed hierarchy pairs become GENERALIZES. |
| RDF/RDFS (declared mappings) | `schema/conformance.json` declares each mapping as a subject-predicate-object triple (`rdfs:subClassOf`, `rdfs:subPropertyOf`, `rdfs:seeAlso`, or a project annotation `kg:mapsTo…`). `etl.conformance.validate_ontology` checks that every mapping names a schema term, uses an allowed predicate and a known vocabulary, and that every declared vocabulary is used; the audit also checks that every label and relation in the graph is declared with its domain and range. No RDF file, RDF export or OWL reasoning is claimed. |
| Dublin Core / ISO 15836 | The field correspondences of [`ontology.md`](ontology.md#alignment-with-other-vocabularies) are declared and checked. |
| ISO 26324 (DOI) | A DOI is `10.<4–9 digits>/<suffix without whitespace>`; no DOI is made up; the raw citation and its parse status are kept. |
| ISO 8601 | `retrieved_at` and `source_date` are full dates, `YYYY-MM-DD`; page header dates keep the catalog's `YYYY-MM` and validate as ISO year-month. |

## Codes and identifiers

| Code | Standard | On | Rule |
|---|---|---|---|
| DOI | ISO 26324 | `Paper.doi` | as written in the citation, syntax checked |
| arXiv id | arXiv identifier scheme, `YYMM.NNNNN` | `Paper.arxiv_id` | as written |
| DBLP key | DBLP record key | `Paper.dblp_key` | as written; never looked up |
| Dates | ISO 8601 | `retrieved_at`, `source_date`, header dates | see above |
| Source version | Git commit SHA-1 | `DataSource.version`, every `source_url` | the pinned commit `5fff7f74508a52ac238f3bb608b8c8c872489fec` |
| Source location | URL | `source_url` | `https://github.com/samyama-ai/dbms_research/blob/<commit>/<file>` |

Node ids are this project's own; their patterns are in
[`taxonomy.md`](taxonomy.md#identifiers).

### What is not used

| Standard | Why not |
|---|---|
| ORCID, DBLP person ids | No lookup outside the catalog in this build; `Person.dblp_pid` and `orcid` stay empty |
| ACM Computing Classification System | The catalog has its own 35 topics; a crosswalk would be our claim, not the page's |
| OWL | No reasoning is done or promised; mappings are declared triples, checked by a test |

## Query language and interfaces

| Interface | Standard |
|---|---|
| Queries | openCypher, as implemented by Samyama Graph |
| Tools for agents | Model Context Protocol (`mcp_server/`) |
| Saved graph | Samyama `.sgsnap` snapshot, with a JSON manifest of its SHA-256 and counts |

## Licences

| What | Licence |
|---|---|
| The catalog, and so the graph's content | CC BY 4.0, `samyama-ai/dbms_research` |
| This repository's code | Apache 2.0 |

## Provenance and boundary rules

- **Ids are deterministic.** Problem and Topic keep the catalog's ids; Paper ids are `paper:` and
  24 hex characters of SHA-256 over the merged work's representative citation; other ids hash a normalised
  key or use the position in the page. Duplicate ids are refused.
- **Dates come from the lock record.** `retrieved_at` and `source_date` are read from
  `data/dbms_research.lock.json`. A missing date fails conformance; no current time or placeholder
  is written.
- **Every node points at its page.** Page-derived nodes carry a commit-pinned `source_url`; shared
  nodes keep the first page in id order and a `page_count`. `source = dbms_research`,
  `provenance = real`.
- **Citations are the catalog's.** `verification_status` is `source_only` or `unverified`; no
  independent check is claimed, and no external metadata is fetched.
- **Edges keep to their declared ends.** Relation pairs are unique per type, both ends exist, and
  each edge joins the labels `schema/conformance.json` allows.
- **Institutions come from a checked list** (`INSTITUTIONS` in `etl/source_entities.py`), matched
  in §7; an Institution's ACTIVE_ON edge keeps the §7 item as `direction`.
- **Affiliations are what the page states.** AFFILIATED_WITH comes only from a §7 bracket such as
  "Suciu (UW)" or "TUM (Neumann, Leis)", only when exactly one author on the same page has that
  surname, and never from several names before several institutions. The edge keeps the matched
  text as `evidence`. It is not a verified current affiliation.
- **Nothing is inferred** about a person's identity, funding, the problem's status after the pinned
  commit, or global citation counts.

## Acceptance evidence

On 2026-10-16 the build of the pinned commit (20,211 nodes, 53,721 edges) passes the structural
checks of `python -m etl.local_graph verify`, the 18 content criteria of `python -m etl.quality`
([quality report](quality-report.md)), the 22 items of `python -m etl.audit`
([audit report](audit-report.md)) and the 48-question check of `python -m benchmarks.reference`
([benchmark](../benchmarks/scope_questions.md)). All 16 labels and 17 relations are populated.
The project-owned taxonomies, crosswalks, institution list and concept hierarchy still need a
reviewer's approval before a production load; their assignments are `rule-based`, never
"verified".
