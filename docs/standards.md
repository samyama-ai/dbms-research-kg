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

1. **DBMS topic taxonomy** (scheme `dbms-topic`): 35 flat, source-ordered topic folders from pinned
   `TAXONOMY.md`; `Problem→Topic` is exactly one-to-one per page. No inferred
   parent groupings.
2. **Problem type** (scheme `problem-type`): flat codes `query-evaluation`, `query-optimization`,
   `data-modeling`, `data-integration`, `transaction-processing`,
   `storage-indexing`, `distributed-data`, `analytics`, `system-design`,
   `other`, `unclassified`. First matching explicit keyword rule over title and
   §1 is primary (`problem_type_method=statement-rule`, evidence = title and §1).
   When no rule fires, the page's own topic decides through the documented
   `TOPIC_PROBLEM_TYPE` crosswalk in `etl/source_entities.py`
   (`problem_type_method=topic-crosswalk`, evidence = the topic id). Both are
   `rule-based`; `unclassified` remains only if neither applies.
3. **Solution/technique family** (scheme `solution-technique-family`): flat codes `join-processing`,
   `query-optimization`, `decomposition`, `indexing`,
   `transaction-processing`, `distributed-processing`, `analytics`, `storage`,
   `relational-dbms`, `analytical-dbms`, `streaming-system`, `query-engine`,
   `other`, `unclassified`. A name rule over the algorithm/system name decides
   first (`family_method=name-rule`). Otherwise the majority topic of the pages
   that cite the name as state of the art decides through the
   `TOPIC_TECHNIQUE_FAMILY` crosswalk (`family_method=topic-crosswalk`, evidence
   `topic NN`). Both are `rule-based`.
4. **Computational model/workload** (scheme `computation-model-workload`): flat codes `word-ram`, `cell-probe`,
   `external-memory`, `comparison`, `streaming`, `parallel`, `turing`,
   `fine-grained` (SETH, 3SUM, APSP, OMv), `complexity-class` (NP, coNP, PSPACE,
   W[1], undecidability), `information-theoretic`, `distributed-impossibility`
   (CAP, FLP, PACELC), `online` (competitive analysis), `communication`,
   `cryptographic`, `statistical`, `other`, `unclassified`. A model requires a
   matching explicit phrase in §4/§5 (`MODELS` in `etl/source_entities.py`).

Besides these four taxonomies, the project-owned **concept scheme** has 90 concepts
matched in §2 (`CONCEPTS`), with 31 reviewed `GENERALIZES` (skos:broader)
pairs in `CONCEPT_HIERARCHY`. Each pair carries `method=curated-hierarchy` and a
one-sentence `rationale` citing the textbook relation; a pair is emitted only
when both concepts occur in the graph.

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
   The page's own bold verdict wins (`stated`). Keyword rules ignore bold
   markers; a closed phrase together with an open, partial or empirical phrase
   gives `partially-solved`, because only part of the gap is closed.
4. `Bound.kind`: `time`, `space`, `impossibility`, `approximation`,
   `unclassified`. Rules in `etl/classify.py`: a lower bound with hardness or
   impossibility wording is `impossibility`; otherwise complexity notation or
   time words give `time`, space words `space` (the more frequent wins when both
   occur); approximation-ratio or error guarantees give `approximation`.
5. `STATE_OF_ART.kind`: `theory`, `systems`.
6. `Person.name_form`: `full`, `initials`, `surname`.
7. `Venue.kind`: `conference`, `journal`, `preprint`, `book`, `report`, `other`
   (`report` covers technical reports, theses and vendor documentation).
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
- Institutions come only from the checked list `INSTITUTIONS` in
  `etl/source_entities.py`, matched in §7; an `Institution→Problem` `ACTIVE_ON`
  edge cites the problem page and keeps the §7 item as `direction`.
- `AFFILIATED_WITH` comes only from §7 bracket patterns ("Suciu (UW)",
  "TUM (Neumann, Leis)") and only when exactly one author cited on the same page
  has that surname; the edge keeps the matched text as `evidence`. It records
  what the page states, not a verified current affiliation.
- No person identity resolution, funding, post-snapshot status, global citation
  count, or external bibliography record may be inferred.

## Acceptance evidence and current limits

As of 2026-10-16 the v5 candidate
(`build/dbms_research_kg.schema-candidate-v5.sqlite`, 21,381 nodes, 55,314
edges) passes the structural checks, all seven alignments, and the 18 content
criteria of `python -m etl.quality`; the generated
[quality report](quality-report.md) lists each measurement. Every one of the 16
labels and 17 relationship types is populated. Three labels stay below the
2026-09 graph by design (Paper, Institution, Algorithm), each explained in the
report. The project-owned taxonomies, crosswalks, institution list and concept
hierarchy still need human review before a production load; their assignments
are `rule-based`, never "verified". The 48-question acceptance check is the
next step.
