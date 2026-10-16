# Historical schema conformance inventory (pre-clone)

This is a first-pass mapping against the checked-in `docs/schema.md` (v0.1 plan),
`docs/scope.md`, the current loader, and tests. It records gaps rather than
guessing meanings for requirements that the source schema does not define.

Status means: **present** = directly represented and implemented; **partial** =
some behavior exists but the requirement is not fully implemented or validated;
**missing** = no implementation found; **underspecified** = the requested
definition is absent from the schema source of truth and cannot be safely
implemented until specified.

## Ontology and vocabulary alignments (7)

| Required alignment | Schema element / graph representation | Code / test evidence | Status |
|---|---|---|---|
| Project DBMS domain ontology | No ontology namespace, class/property IRIs, or alignment axioms in `docs/schema.md` | No RDF/OWL export or mapping code found | Underspecified |
| PROV-O | Schema §4 has project-specific provenance fields, but no PROV-O terms/mapping | Loader stores source fields; no PROV-O mapping/tests | Partial |
| SKOS | Topic/concept hierarchy is described informally; no SKOS predicates or URI policy | Allow-listed Concepts only; no SKOS serialization/tests | Partial |
| Dublin Core Terms | Paper/source fields exist; no `dcterms:` mapping | Citation parser emits local fields only | Underspecified |
| FOAF | Person exists; no FOAF class/property mapping | Person extraction exists; no FOAF mapping/tests | Underspecified |
| Schema.org | Paper/Person/Venue resemble types, but no mapping is defined | No mapping code/tests | Underspecified |
| CiTO | CITES has a local role property; no CiTO relation mapping | CITES extraction exists; no CiTO terms/tests | Partial |

## Taxonomies (4)

| Required taxonomy | Schema/source element | Code / test evidence | Status |
|---|---|---|---|
| 35-topic DBMS taxonomy | `Topic`, `IN_TOPIC`; source `TAXONOMY.md` per schema §2 | Parser reads source topic folders; loader emits Topic/IN_TOPIC | Present, but no conformance assertion for all taxonomy metadata |
| Problem-type taxonomy | No definition in `docs/schema.md` | No `Problem.problem_type` mapping found | Underspecified |
| Solution/technique-family taxonomy | No definition in `docs/schema.md` | No `Algorithm.family`/`System.family` mapping found | Underspecified |
| Computational-model/workload taxonomy | `ComputationModel` is named, but no taxonomy hierarchy/controlled values | Source phrase matching for models; no taxonomy hierarchy tests | Partial |

## Controlled code lists (12)

| Code list | Exact allowed values in schema | Current code / graph mapping | Status |
|---|---|---|---|
| `Problem.status` | `open`, `partially-solved`, `empirically-open`, `solved-but-impractical`, `stale` | Parser accepts first four; catalog has no `stale` pages | Partial |
| `CITES.role` | `foundational`, `sota`, `survey`, `systems`, `docs`, `artifact`, `attack` | Citation parser normalizes source tag; no validator found | Partial |
| `Gap.verdict` | `open`, `partially-solved`, `empirically-open`, `closed`, `unstated` | No Gap node/extraction | Missing |
| `Bound.kind` | `time`, `space`, `impossibility` | Loader classifier can also return `unspecified`, outside the listed values | Partial; violates stated list |
| `STATE_OF_ART.kind` | `theory`, `systems` | Loader emits these kinds for allow-listed matches | Partial; no validator |
| `Person.name_form` | `full`, `initials`, `surname` | Person extraction exists; no `name_form` assignment found in inspected loader | Missing |
| `Venue.kind` | `conference`, `journal`, `preprint`, `other` | Venue extraction exists; no kind classification | Missing |
| `Institution.kind` | `academic`, `industry`, `government`, `non-profit` | Institution extraction is explicitly deferred in Phase 3 log | Missing |
| `Problem.problem_type` | No values listed in `docs/schema.md` | No mapping found | Underspecified |
| `Algorithm.family` / `System.family` | No values listed in `docs/schema.md` | Allow-listed entity mentions only; no family properties | Underspecified |
| `ComputationModel.class` | No values listed in `docs/schema.md` | Model mentions extracted, no class property | Underspecified |
| `CLASSIFIED_AS.evidence_status` | No edge or values defined in `docs/schema.md` | `CLASSIFIED_AS` not implemented | Underspecified |

## Standards/specification groups (6)

| Group | Current schema statement | Code/tests | Status |
|---|---|---|---|
| PROV-O | No standards conformance section or mapping | None | Missing |
| SKOS | No standards conformance section or mapping | None | Missing |
| RDF/RDFS/OWL | Schema specifies a labelled property graph and openCypher, not RDF serialization/semantics | None | Missing |
| Dublin Core / ISO 15836 | Not named in the schema | None | Missing |
| ISO 26324 | DOI field is planned, but no standard identifier validation | DOI pattern extraction only; no validation test | Partial |
| ISO 8601 | Dates are described as header values; no datatype/format requirement stated | Parser carries date strings; no validation test | Partial |

## Core schema and source rules

| Requirement from `docs/schema.md` | Schema element | Implementation / tests | Status |
|---|---|---|---|
| Stable identifiers | §2 defines IDs and paper title normalization | Stable IDs and citation identity helpers; tests cover retry/citation identity | Partial: no exhaustive per-type stability test; legacy ID handling remains |
| Provenance on every node | §4: `provenance`, `source`, `method`, `retrieved_at`, `source_date`, `source_url`/`page_count` rules | Current loader primarily stores `source_path`; required common fields are not all emitted | Missing |
| Source boundary | Pinned commit in schema header; source-only catalog; no unapproved enrichment | Loader checks catalog pin and parser validates it; no graph-wide provenance audit | Partial |
| Evidence status | No general evidence-status definition in v0.1 schema; citation parse/verification fields are local extensions | Citation parser keeps raw text and parse status; no graph-wide evidence status | Underspecified |
| Validation constraints | Schema gives property shapes and some code lists, but no complete machine-readable constraints | Source parser checks required sections/status; no graph schema/conformance validator | Partial |
| Node/edge inventory | Schema §2 lists 15 labels; §3 lists 16 edge types | Phase 3 log records 11 labels and 9 edge types implemented | Partial |
| Relationship direction and endpoint labels | Schema §1–3 diagram/table | Tests cover nine current relation shapes, including `CITES: Problem→Paper`, `AUTHORED_BY: Paper→Person`, `APPEARED_AT: Paper→Venue` | Partial; seven planned edges have no mapping/tests |

## Research questions and validation

`docs/scope.md` defines 48 questions. The current tests in `tests/test_loader.py`
exercise parsing, identity, extraction, and loader retry behavior; they are not a
48-question answer/refusal suite. The schema maps question groups in §7 but
explicitly marks Q34 and Q41 partial, Q39 engine-limited, and Q46–48 as required
refusals. No executable expected-answer/refusal harness was found.

| Questions | Expected behavior from `docs/scope.md` | Existing executable coverage | Status |
|---|---|---|---|
| Q1–8, Q10, Q12, Q14–17, Q20, Q23–26, Q30–33, Q35–36, Q40, Q42–43 | Answer from documented graph/query fields | No 48-question query suite found | Missing as tests; implementation coverage varies |
| Q9, Q18–19, Q21–22, Q27–29, Q37–39, Q44–45 | Partial/fixed answer as described in scope | No 48-question query suite found | Missing as tests; implementation coverage varies |
| Q11, Q13, Q34, Q41 | Gap/research-direction additions; Q34/Q41 partial as documented | Gap and ResearchDirection absent from current loader inventory | Missing/partial |
| Q46–48 | Must refuse: global citations, post-snapshot resolution, funding | No refusal harness found | Missing |

## Clone gate and safe sequence

No graph write has been performed for this checklist. The repository documents
that the reference snapshot is `dbms-research.sgsnap` (`kg-snapshots-v10`) with
20,019 nodes and 39,393 edges. The upstream Samyama README documents snapshot
**import** at `POST /api/snapshot/import`, but this repository does not document
an export operation from the running 8092 instance. Therefore an exact live
clone procedure is not yet established: importing the published snapshot is
only equivalent if its bytes/version are confirmed to be the exact artifact
loaded at 8092.

Before any graph write, establish one of these auditable sources:

1. The exact `.sgsnap` artifact loaded into 8092, with checksum and version; or
2. The supported engine export command/API for 8092, with a read-only export and
   checksum.

Then import it into a newly created isolated instance on a free port (not 8092
or 8093), query its counts, and require exactly 20,019 nodes and 39,393 edges
before refinement. Do not run the loader against 8093. Do not reset either
existing instance.

The requested ontology mappings, additional taxonomies, and additional code
lists needed normative definitions; the v1 requirements are now recorded in
`docs/schema.md`, `docs/standards.md`, and `schema/conformance.json`. The current
audit and candidate result follow below; the historical findings above remain as
the pre-implementation record.

## Current audit and conformance matrix (2026-10-15)

### Artifacts and actual counts

The existing artifact `build/dbms_research_kg.sqlite` remains unchanged. Its
read-only verification is 20,019 nodes, 40,189 relationships, 12 populated
labels, and 13 populated relationship types. It retains snapshot records whose
per-record upstream source paths are not available. A SQLite backup at
`build/dbms_research_kg.preconformance-backup-20261015.sqlite` passed
`PRAGMA integrity_check` and has the same 20,019/40,189 totals.

The separate catalog-only candidate is
`build/dbms_research_kg.schema-candidate-v2.sqlite`. It uses the pinned catalog
only, because the snapshot cannot establish each imported record's provenance
under v1 rules. The expected actual totals are 19,676 nodes and 41,916 edges;
16 schema labels and 17 schema relationship types are declared, of which 15
labels and 15 types are populated. `Institution`, `AFFILIATED_WITH`, and
`GENERALIZES` are empty. Empty types are retained in the schema inventory and
are not filled with guessed records.

### Node label/property matrix

Required and optional fields are defined machine-readably in
[`../schema/conformance.json`](../schema/conformance.json). The candidate was
reopened and checked against every required field; zero missing fields were
reported. The candidate property records and actual counts are:

| Label | Candidate count | Required properties | Optional properties / current gap |
|---|---:|---|---|
| Problem | 1,053 | `id`, `title`, `slug`, `status`, `statement`, `worked_example` | review dates, reference flags, `problem_type`, source-page sections and topic link fields |
| Topic | 35 | `id`, `number`, `name`, `slug` | `scope` (not present in catalog rows) |
| Paper | 2,934 | `id`, `citation_text`, `parse_status` | title, year, DOI, arXiv/DBLP key, URL, raw venue/authors, page count; title may be empty only for `uncertain` parse |
| Person | 5,267 | `id`, `name`, `name_form` | DBLP PID, ORCID, aliases; not resolved from external sources |
| Venue | 800 | `id`, `name`, `kind` | source/page-count provenance; venue kind remains conservative and not independently validated |
| Institution | 0 | `id`, `name`, `kind` | no checked source list supports institution records |
| Concept | 10 | `id`, `name` | aliases and allow-list extraction evidence |
| Algorithm | 3 | `id`, `name`, `family` | page count and allow-list evidence; only source-section matches |
| System | 17 | `id`, `name`, `kind`, `family` | page count and allow-list evidence; only source-section matches |
| Bound | 2,106 | `id`, `problem_id`, `direction`, `kind`, `text` | none required beyond page provenance |
| ComputationModel | 7 | `id`, `name`, `class` | page count and source phrase evidence |
| Gap | 1,053 | `id`, `problem_id`, `text`, `verdict`, `verdict_raw`, `verdict_method` | none beyond page provenance |
| ResearchDirection | 2,496 | `id`, `problem_id`, `text`, `frontier` | none beyond page provenance |
| FutureDirection | 3,825 | `id`, `problem_id`, `text` | none beyond page provenance |
| DataSource | 1 | `id`, `name`, `url`, `version`, `licence` | pinned catalog source only |
| TaxonomyTerm | 69 | `id`, `scheme`, `code`, `name`, `notation` | terms are project-schema vocabulary, not claimed research entities |

Every candidate node has `provenance`, `source`, `method`, `retrieved_at`,
`source_date`, and `source_url`; shared entities also have a positive `page_count`.
The validator checks ISO 8601 full dates, source boundary, DOI syntax, paper
year type, Problem year-month dates, and controlled properties. Node IDs and
logical identities are unique in the candidate. This is structural provenance
evidence; it does not prove a citation's bibliographic truth or a person's
real-world identity.

### Relationship endpoint/property matrix

The candidate's data validator checks every edge endpoint, endpoint label,
required edge property, unique typed endpoint pair, and source commit. Counts are
actual rows; zero rows are explicit:

| Relationship | Direction | Required properties | Count | Candidate evidence/status |
|---|---|---|---:|---|
| IN_TOPIC | Problem → Topic | none | 1,053 | source topic assignment; exactly one per Problem |
| CITES | Problem → Paper | `role`, `position`, `verification_status` | 6,157 | raw role retained when present; `source_only`/`unverified` is not external verification |
| AUTHORED_BY | Paper → Person | `position` | 9,879 | authors parsed from citation text; ambiguous written-name variants remain distinct |
| APPEARED_AT | Paper → Venue | none | 3,219 | venue extracted only when parser finds explicit citation boundary |
| RESTS_ON | Problem → Concept | none | 303 | exact allow-listed §2 matches |
| GENERALIZES | Concept → Concept | none | 0 | no reviewed hierarchy-pair inventory; no edges invented |
| HAS_BOUND | Problem → Bound | `direction` | 2,106 | source bound text retained |
| IN_MODEL | Bound → ComputationModel | none | 259 | model phrase matched from §4/§5 |
| STATE_OF_ART | Problem → Algorithm/System | `kind` | 663 | exact allow-listed §3 matches |
| HAS_GAP | Problem → Gap | none | 1,053 | §6 text and extraction method retained |
| HAS_RESEARCH | Problem → ResearchDirection | `position` | 2,496 | §7 item text retained |
| CLOSING_REQUIRES | Problem → FutureDirection | `position` | 3,825 | source item and zero-based source order retained |
| ACTIVE_ON | Person/Institution → Problem | `direction` | 3,652 | exact normalized authored-name mention in §7; means named there, not verified current activity |
| AFFILIATED_WITH | Person → Institution | none | 0 | external affiliation claims excluded |
| RELATED_TO | Problem → Problem | `method`, `score`, shared-evidence count | 4,065 | recomputed; requires ≥2 distinct shared catalog papers/concepts; source URLs checked |
| FROM_SOURCE | Problem → DataSource | none | 1,053 | points to the one pinned catalog record |
| CLASSIFIED_AS | Problem/Algorithm/System/ComputationModel → TaxonomyTerm | `evidence_status`, `evidence` | 2,133 | membership, code, evidence, and status validated |

`CITES`, `AUTHORED_BY`, `APPEARED_AT`, and `RELATED_TO` directions are checked
against the exact endpoint contracts. Candidate verification reported zero
endpoint errors, foreign-key errors, duplicate logical nodes, duplicate
relationships, provenance errors, and schema-data errors.

### Ontology/vocabulary alignment matrix (7)

| Alignment | Required mapping | Candidate/code evidence | Status / gap |
|---|---|---|---|
| Project DBMS domain ontology | project namespace, all 16 classes and 17 object properties with domains/ranges | TTL parsed; every class and relationship contract checked against candidate rows | PASS on source-only v1 candidate; FAIL on legacy 12-label/13-type graph |
| PROV-O | source locator/derived-from/retrieval field mapping without false entity assertions | TTL mapping and candidate node/edge provenance coverage checked | PASS on candidate field/edge contract; no PROV RDF instance serialization is required |
| SKOS | `Topic`, `Concept`, and taxonomy terms; notation, schemes and evidenced hierarchy | 35 topics, 69 taxonomy terms, 2,133 `CLASSIFIED_AS` memberships; exact code sets checked | PASS for candidate term membership; no supported `GENERALIZES` pairs, so hierarchy is empty |
| Dublin Core Terms | title, creator, issued, subject, relation/source correspondences | TTL mapping plus actual Paper/author/topic/relation rows checked | PASS for candidate’s documented LPG correspondences; RDF instance serialization is not required |
| FOAF | Person/Institution class and name correspondences | Actual Person and Institution records and names checked | PASS for present rows; candidate has zero Institution rows and makes no affiliation claim |
| Schema.org | Paper, Person, Institution, Venue see-also mappings | TTL mappings and corresponding candidate record/name/title coverage checked | PASS for the documented see-also correspondences; no RDF instance export is required |
| CiTO | `CITES` plus role annotations and persisted `cito_property` | All citation edges carry source role and mapped CiTO property; two `artifact` citations are mapped from their cited source URLs and actual meaning | ClockBound software uses generic `cito:cites` with a documented fallback; CEB benchmark/workload uses `cito:citesAsDataSource`; unknown artifacts use noted generic fallback |

`etl.conformance.validate_ontology` uses rdflib for Turtle syntax, namespace,
class/object-property declarations, domains/ranges, datatype-property
declarations, all machine-inventoried correspondence triples, and CiTO role
annotations. The project `.venv` now has rdflib 7.6.0; it reports PASS with
183 parsed triples. This checks the mapping artifact, not RDF instance triples
inside SQLite and not OWL reasoning.

### Taxonomy matrix (4)

| Taxonomy | Defined membership | Current candidate | Status / source limits |
|---|---|---|---|
| DBMS topic | 35 flat source topics | 35 terms; all 1,053 Problems have one `IN_TOPIC` and one source-explicit taxonomy edge | PASS for membership/direction; scope text absent and no inferred parent hierarchy |
| Problem type | 11 project-owned flat codes | 1,053 assignments with source text and rule-based/unresolved status | PARTIAL: rule vocabulary is project-defined; semantic categories need human review |
| Solution/technique family | 14 project-owned flat codes | 3 Algorithms and 17 Systems classified; rule evidence stored | PARTIAL: conservative allow-list coverage only; no external entity enrichment |
| Computational-model/workload | 9 project-owned flat codes | 7 models classified from source §4/§5 phrases | PARTIAL: phrase coverage is limited and class mapping is rule-based |

All term sets and assigned code memberships are checked from actual candidate
rows. Non-source taxonomy codes have `project_schema` provenance; assignments
record `source-explicit`, `rule-based`, or `unresolved` and the evidence text.
The three project-defined taxonomies are not upstream source taxonomies; they
remain a human-governance choice.

### Controlled coding systems (12)

The validator checks the following exact values on prepared and persisted
candidate records. “PASS (values)” means code membership is validated, not that
every heuristic classification is substantively correct.

| Code list | Allowed values | Candidate/status |
|---|---|---|
| Problem.status | `open`, `partially-solved`, `empirically-open`, `solved-but-impractical`, `stale` | PASS (values); `stale` is allowed but absent in pinned pages |
| CITES.role | `foundational`, `sota`, `survey`, `systems`, `docs`, `artifact`, `attack`, `mixed`, `unclassified` | PASS (values); raw tag retained; per-edge `cito_property` checked against the role mapping or cited artifact URL override |
| Gap.verdict | `open`, `partially-solved`, `empirically-open`, `closed`, `unstated` | PASS (values); keyword verdict accuracy is not manually adjudicated |
| Bound.kind | `time`, `space`, `impossibility`, `unclassified` | PASS (values); conservative text rules, many unclassified |
| STATE_OF_ART.kind | `theory`, `systems` | PASS (values) |
| Person.name_form | `full`, `initials`, `surname` | PASS (shape); no identity merge; ambiguous names remain separate |
| Venue.kind | `conference`, `journal`, `preprint`, `other` | PASS (values); some acronym-only venues resolve to `other` due absent type evidence |
| Institution.kind | `academic`, `industry`, `government`, `non-profit` | NOT APPLICABLE: zero institution nodes supported by pinned catalog |
| Problem.problem_type | `query-evaluation`, `query-optimization`, `data-modeling`, `data-integration`, `transaction-processing`, `storage-indexing`, `distributed-data`, `analytics`, `system-design`, `other`, `unclassified` | PASS (values); PARTIAL semantics (project rules) |
| Algorithm.family / System.family | `join-processing`, `query-optimization`, `decomposition`, `indexing`, `transaction-processing`, `distributed-processing`, `analytics`, `storage`, `relational-dbms`, `analytical-dbms`, `streaming-system`, `query-engine`, `other`, `unclassified` | PASS (values); PARTIAL coverage and rule semantics |
| ComputationModel.class | `word-ram`, `cell-probe`, `external-memory`, `comparison`, `streaming`, `parallel`, `turing`, `other`, `unclassified` | PASS (values); PARTIAL phrase coverage |
| CLASSIFIED_AS.evidence_status | `source-explicit`, `rule-based`, `unresolved` | PASS (values and evidence presence); semantic audit of all rules remains |

### Standards/specification groups (6)

| Group | Executable rule/evidence | Status |
|---|---|---|
| PROV-O | required provenance/date fields and source edges checked in candidate | PASS for the declared field/edge mapping; no RDF export or PROV activity/entity model claimed |
| SKOS | term schemes/notations and exact membership sets checked | PASS for candidate taxonomy membership; empty hierarchy is allowed absent evidence |
| RDF/RDFS/OWL | Turtle declarations, domains/ranges, and mapping triples parsed by rdflib | PASS for syntax and implemented structural mapping checks; no reasoner or RDF instance export |
| Dublin Core / ISO 15836 | field/edge mapping declarations and required source data fields | PASS for documented LPG correspondences; no RDF instance export |
| ISO 26324 | DOI syntax regex; raw citation and parse status retained; no DOI synthesized | PASS for syntax only; external DOI resolution intentionally not performed |
| ISO 8601 | full dates validated with `date.fromisoformat`; source review dates validated `YYYY-MM` | PASS for stored formats |

### Identity, coverage and `RELATED_TO`

The source catalog itself has multiple written author forms at the same
deduplicated Paper position: 1,729 paper-position groups across 692 Papers have
more than one Person node. The existing snapshot has 1,036 such groups. In the
target acyclic-join-dependencies Paper, the source citation lists four authors,
while four stored author positions each have two Person endpoints. Full-name
snapshot records carry matching initials aliases/authority keys in several
cases; surname-only records do not. These are unresolved identity variants,
not safe merge candidates. No Person records are merged or deleted.

The source-only candidate has 2,934 Paper nodes and 6,157 CITES edges. 29 Paper
records have no parsed title and are preserved as `uncertain` with raw citation
text instead of fabricated titles. Paper identity groups by DOI or normalized
title/year; representative IDs remain legacy-compatible SHA-256 IDs. Author
and venue variants remain distinct when source evidence cannot safely disambiguate.

The existing graph's 3,610 `RELATED_TO` edges consist of 441 snapshot edges
without retained shared-evidence metadata and 3,169 catalog-derived edges. All
3,169 catalog-derived edges have method `shared-papers-concepts`, at least two
shared evidence items, and source URLs. The candidate recomputes its 4,065
`RELATED_TO` edges from source CITES/RESTS_ON facts and validates each score and
evidence count. The 441 snapshot edges are not carried into the source-only
candidate because their original evidence cannot be reconstructed with certainty.

### Implementation/change status and commands

Implemented in this stage: required property and controlled-value checks;
relationship endpoint/provenance checks; exact taxonomy-term membership and
classification evidence checks; recomputed `RELATED_TO` integrity; source-only
catalog SQLite materialization; safe matching-signature resume; SQLite integrity
check; and optional semantic Turtle parser support. No live graph was written.

Focused verification commands (not the 48-question suite):

```bash
./.venv/bin/python -m pytest -q tests/test_conformance.py tests/test_loader.py
./.venv/bin/python -m etl.local_graph build-catalog-candidate \
  --catalog build/source_catalog.json \
  --output build/dbms_research_kg.schema-candidate-v2.sqlite
./.venv/bin/python -m etl.local_graph verify \
  --graph build/dbms_research_kg.schema-candidate-v2.sqlite
```

The v1 catalog candidate is **not fully ontology conformant** because CiTO's
the two `artifact` meanings are resolved per citation in the candidate; the existing 12-label/13-type graph
is not v1 conformant. Source data does not support Institution/AFFILIATED_WITH
or GENERALIZES claims. The original graph and its row-identical verified backup
remain the rollback artifacts.

### Read-only legacy-versus-v1 audit (2026-10-16)

The legacy graph was inspected read-only at 20,019 nodes and 40,189 edges. Its
12 labels and 13 relationships match the snapshot contract but do not match v1.
The current v1 candidate remains at 19,676 nodes and 41,916 edges; the candidate
has 16 declared labels / 17 declared relationship types and populates 15 / 15.
The v1 candidate uses only the pinned catalog because snapshot-only rows have
artifact-level rather than per-record source paths. The legacy graph is
unchanged and can be restored from the verified backup at
`build/dbms_research_kg.preconformance-backup-20261015.sqlite`.

| Alignment | Legacy graph status | v1 candidate status | Basis / remaining condition |
|---|---|---|---|
| Project DBMS domain ontology | FAIL | PASS | Legacy is missing `Gap`, `ResearchDirection`, `DataSource`, `TaxonomyTerm` and `HAS_GAP`, `HAS_RESEARCH`, `FROM_SOURCE`, `CLASSIFIED_AS`; candidate conforms to machine inventory. |
| PROV-O | PARTIAL | PASS | Legacy nodes/edges lack per-record v1 provenance fields; candidate has no missing required provenance fields. Mapping is field/edge-level, not full PROV serialization. |
| SKOS | PARTIAL | PASS | Legacy has Topic/Concept and one unreviewed `GENERALIZES`, but no taxonomy terms/classification edges; candidate has 69 taxonomy terms and 2,133 checked classification edges. |
| Dublin Core Terms | PASS | PASS | Title/year where available and creator/subject/relation graph correspondences are present; incomplete/uncertain citation data remains explicit. |
| FOAF | PASS | PASS | Names exist for stored Person/Institution nodes in legacy and Person nodes in candidate; candidate has zero Institution records and makes no affiliation claims. |
| Schema.org | PASS | PASS | Candidate/legacy records have the required mapped fields for the documented see-also mappings; no RDF instance export is required. |
| CiTO | PARTIAL | PASS (v4) | Legacy has 6,116/6,528 CITES edges with only legacy `prop`; v4 has 6,157 edges with validated role mappings. ClockBound is software/service (`cito:cites`) and CEB is benchmark/workload (`cito:citesAsDataSource`), preserving the source role. |

`validate_ontology()` parsed the Turtle with rdflib 7.6.0 and passed: 183
triples; all inventoried classes, object-property domains/ranges, datatype
properties, mapping triples, and CiTO role annotations passed. This is syntax
and mapping-artifact evidence, not RDF instance serialization or OWL reasoning.
`validate_sqlite_alignments()` separately checks persisted graph labels, edge
types/endpoints, required fields, taxonomy terms, provenance fields, and
alignment-specific data coverage. The candidate reports zero duplicate logical
nodes/edges, endpoint errors, provenance errors, required-property errors, or
schema-data errors; SQLite integrity is `ok`.

The candidate's counts and rows did not change in this pass. The existing
candidate builder safely refreshed only its schema/ontology/implementation
signature after comparing every persisted node and edge row with fresh
in-memory output from the pinned catalog. A repeated build produced the same
counts. No 48-question tests were run.
