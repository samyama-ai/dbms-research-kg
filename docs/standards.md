# Standards, vocabularies, taxonomies, and coding systems

Normative companion to [`schema.md`](schema.md), version 1.0. Values extracted
from pages remain bounded by the pinned `dbms_research` commit. Vocabulary terms
defined here describe the schema; a classification edge is emitted only when a
page contains evidence or an explicit rule records its uncertainty.

## Ontology and vocabulary alignment inventory (7)

The machine-readable class/property mapping is [`../schema/dbms_research_kg.ttl`](../schema/dbms_research_kg.ttl).
The project namespace is `https://samyama.ai/kg/dbms-research/ontology#`.

| Alignment | Mapping contract | Assertion limits |
|---|---|---|
| Project DBMS domain ontology | Local classes and properties in the Turtle ontology; exact graph endpoint domains/ranges are in `schema/conformance.json` | Defines project terms, not external facts |
| PROV-O | `source_url` locates `prov:hadPrimarySource`; `FROM_SOURCE` maps to `prov:wasDerivedFrom`; `retrieved_at` is related to `prov:generatedAtTime`; `method` names a local extraction activity | Do not assert string literals as PROV entities or equate retrieval and generation time |
| SKOS | `Topic`, `Concept`, and `TaxonomyTerm` are SKOS concepts; topic numbers are notation; broader/narrower links are only asserted for enumerated hierarchy pairs | The 35 source topics are flat; no invented parent topic |
| Dublin Core Terms | `Paper.title`→`dcterms:title`; authorship edge→`dcterms:creator`; `Paper.year`→`dcterms:issued`; `IN_TOPIC`→`dcterms:subject`; `RELATED_TO`→`dcterms:relation` | Graph field/edge mapping only; no RDF export claimed |
| FOAF | `Person`→`foaf:Person`; `Institution`→`foaf:Organization`; names→`foaf:name` | Catalog names do not verify real-world identity or affiliation |
| Schema.org | `Paper` see-also `schema:ScholarlyArticle`; `Person` see-also `schema:Person`; `Institution` see-also `schema:Organization`; `Venue` see-also `schema:Periodical`/`schema:EventSeries` | Similarity links, not subclass claims where venue kind is unknown |
| CiTO | `CITES`→`cito:cites`; roles map as follows | Nearest-term mappings are annotations, not asserted CiTO citation triples |

`schema/dbms_research_kg.ttl` defines the labelled-property-graph schema and
its field correspondences. The project does not require RDF instance triples
inside SQLite. `kg:mapsTo` is explicitly non-entailing: a future RDF exporter
must apply the correspondence and preserve the distinction between a literal
locator and a PROV entity. The PROV retrieval-time correspondence does not
assert that retrieval time is entity generation time. The `CLASSIFIED_AS` to
`skos:related` correspondence is descriptive, not an OWL entailment.

| `CITES.role` | CiTO property | Confidence |
|---|---|---|
| foundational | `cito:obtainsBackgroundFrom` | nearest meaning |
| sota | `cito:citesAsAuthority` | nearest meaning |
| survey | `cito:citesAsRecommendedReading` | nearest meaning |
| systems | `cito:citesAsDataSource` | nearest meaning; tag semantics are source-specific |
| docs | `cito:citesAsSourceDocument` | nearest meaning |
| artifact | citation-specific mapping; generic fallback `cito:cites` | The source tag is too broad to map uniformly. ClockBound is software/service and uses generic `cito:cites`; CEB is a benchmark/workload and uses `cito:citesAsDataSource`. Both preserve `role=artifact` and raw source tag. Unknown artifact URLs retain the generic mapping with an explicit rationale. |
| attack | `cito:critiques` | nearest meaning |

## Taxonomies (4)

All are closed schemes in `schema/conformance.json`. The first is source-defined;
the other three are project classification schemes and each assignment records
`CLASSIFIED_AS.evidence_status` (`source-explicit`, `rule-based`, `unresolved`).

1. **DBMS topic taxonomy:** 35 flat, source-ordered topic folders from pinned
   `TAXONOMY.md`; `Problem→Topic` is exactly one-to-one per page. No inferred
   parent groupings.
2. **Problem type:** flat codes `query-evaluation`, `query-optimization`,
   `data-modeling`, `data-integration`, `transaction-processing`,
   `storage-indexing`, `distributed-data`, `analytics`, `system-design`,
   `other`, `unclassified`. First matching explicit keyword rule over title and
   §1 is primary; no match is `unclassified` and evidence status `unresolved`.
3. **Solution/technique family:** flat codes `join-processing`,
   `query-optimization`, `decomposition`, `indexing`,
   `transaction-processing`, `distributed-processing`, `analytics`, `storage`,
   `relational-dbms`, `analytical-dbms`, `streaming-system`, `query-engine`,
   `other`, `unclassified`. Match only allow-listed algorithm/system names and
   explicit name rules; otherwise unresolved.
4. **Computational-model/workload:** flat codes `word-ram`, `cell-probe`,
   `external-memory`, `comparison`, `streaming`, `parallel`, `turing`, `other`,
   `unclassified`. A model requires a matching explicit phrase in §4/§5.

**Unresolved design choice:** no source taxonomy specifies problem-type or
family codes. The above is the v1 project-owned rule vocabulary. A reviewer must
approve it before a production refinement load; until then those assignments
remain `rule-based` or `unresolved`, never “verified”.

## Controlled code lists (12)

Exact values are in `schema/conformance.json` and are enforced by
`etl.conformance.validate`.

1. `Problem.status`: `open`, `partially-solved`, `empirically-open`,
   `solved-but-impractical`, `stale` (the last is permitted but absent in source).
2. `CITES.role`: `foundational`, `sota`, `survey`, `systems`, `docs`,
   `artifact`, `attack`, `mixed`, `unclassified`. `mixed` represents multiple
   recognized source tags on one reference; `unclassified` preserves untagged
   and non-role tags such as `[Lower Bound]`. Original text remains in `role_raw`.
3. `Gap.verdict`: `open`, `partially-solved`, `empirically-open`, `closed`,
   `unstated`; extraction method is separately `stated`, `keyword`, or `none`.
4. `Bound.kind`: `time`, `space`, `impossibility`, `unclassified` (added to
   preserve evidence when prose does not justify one of the three substantive kinds).
5. `STATE_OF_ART.kind`: `theory`, `systems`.
6. `Person.name_form`: `full`, `initials`, `surname`.
7. `Venue.kind`: `conference`, `journal`, `preprint`, `other`.
8. `Institution.kind`: `academic`, `industry`, `government`, `non-profit`.
9. `Problem.problem_type`: the problem-type taxonomy codes above.
10. `Algorithm.family`/`System.family`: the solution/technique-family codes above.
11. `ComputationModel.class`: the computational-model taxonomy codes above.
12. `CLASSIFIED_AS.evidence_status`: `source-explicit`, `rule-based`,
    `unresolved`.

## Standards/specification groups (6)

| Group | Concrete conformance rule |
|---|---|
| PROV-O | Every node has source/provenance/method and lock-derived retrieval/source dates; page-derived nodes have pinned commit `source_url`; `FROM_SOURCE` endpoints match the pinned `DataSource`. This is a field/edge mapping, not a claim of full PROV-O serialization. |
| SKOS | Taxonomy terms carry scheme and notation; topic taxonomy stays flat; only explicitly listed hierarchy edges are allowed. |
| RDF/RDFS/OWL | `schema/dbms_research_kg.ttl` declares classes, object properties, domains, ranges, and alignment triples. `etl.conformance.validate_ontology` parses Turtle with rdflib and checks every machine-inventoried class, object-property domain/range, datatype-property declaration, mapping triple, and CiTO role annotation. Install `pip install -e '.[rdf]'` in the project virtual environment. The current `.venv` has rdflib 7.6.0 and the ontology validator passes. No property-graph RDF instance export or OWL reasoning is claimed. |
| Dublin Core / ISO 15836 | Required field/property correspondences are listed above and declared in the ontology. |
| ISO 26324 | DOI syntax is `10.<4–9 digits>/<non-whitespace suffix>`; no DOI is synthesized; raw citation and parse status are retained. |
| ISO 8601 | `retrieved_at` and `source_date` are full dates `YYYY-MM-DD`; page header review dates preserve source `YYYY-MM` precision and validate as ISO year-month. |

## Identifier, provenance, and boundary rules

- IDs are deterministic: Problem/Topic IDs retain the pinned source identifiers;
  Paper IDs are legacy-compatible `paper:` + first 24 hex SHA-256 of the
  normalized first source citation; other generated IDs use deterministic
  SHA-256 prefixes or the documented per-problem ordinal. Global duplicate IDs
  are rejected.
- `retrieved_at` and `source_date` come only from the matching source lock record.
  Missing lock dates fail conformance; no current-time or placeholder date is
  invented.
- Page-derived nodes carry a commit-pinned GitHub `source_url`; shared nodes
  retain the first source path and page count. `source=dbms_research`,
  `provenance=real`; `method` is one of `parsed`, `list-matched`,
  `keyword-classified`, `computed`, `catalog`.
- Citation `verification_status=source_only|unverified` records catalog evidence
  only. No independent verification is claimed. No external metadata lookup is
  allowed in this build.
- Node IDs must be globally unique; relationship pairs are unique per type;
  each edge must use the exact endpoint labels in `schema/conformance.json`.
  `Problem` has exactly one `IN_TOPIC`; edge endpoints must exist.
- No institution, person identity resolution, funding, post-snapshot status,
  global citation count, or external bibliography record may be inferred.

## Acceptance evidence and current limits

Mention in this document is not implementation evidence. The catalog-only
candidate has executable schema/data checks and a read-only seven-alignment
audit. As of 2026-10-16, the v4 candidate passes the project ontology, PROV-O,
SKOS, Dublin Core Terms, FOAF, Schema.org, and CiTO checks. CiTO validation
checks the persisted mapping on each citation edge and validates the two
source-specific artifact mappings. The legacy snapshot graph remains
nonconformant to the v1 domain schema and has incomplete provenance and citation
roles. Institution/affiliation and concept hierarchy evidence is absent from the
pinned catalog. Some project taxonomy meanings still need human review. The
48-question acceptance suite is deferred; none of these results establishes
question-answer conformance or full OWL reasoning.
