
# DBMS Research KG — Schema (v0.2, implementation plan)

This document defines the planned graph schema for DBMS Research KG v1.
The resource inventory and modeling conventions are documented in
[`docs/standards.md`](standards.md).

**Source-data rule:** all graph instance data must come exclusively from the
pinned `github.com/samyama-ai/dbms_research` catalog. External ontologies,
vocabularies, identifiers and standards may inform the schema and its mappings,
but external records, taxonomy assignments and enrichment data must not be
imported.

The counts in this document are targets until Phase 3 builds the graph and
validation tests confirm the actual implementation.

| Field | Value |
|---|---|
| Version | v0.2 implementation plan |
| Graph model | Labelled property graph, openCypher |
| Graph engine | Samyama Graph 1.11.0 |
| Source | `github.com/samyama-ai/dbms_research` |
| Pinned commit | `5fff7f74508a52ac238f3bb608b8c8c872489fec` |
| Pinned source date | 2026-09-09 |
| Source pages | 1,053 |
| Source licence | CC BY 4.0; retain attribution and provenance |
| Old graph | 12 labels, 13 edge types, 20,019 nodes, 39,393 edges |
| Scope | [`docs/scope.md`](scope.md), 48 questions |
| Resource inventory | [`docs/standards.md`](standards.md) |

## 1. Resource inventory and counting rules

These are the targets for the completed v1 schema. They are not measured graph
counts and must not be reported as implemented until the build is validated.

| Category | Target | Breakdown |
|---|---:|---|
| Ontologies and vocabularies | 7 | 1 project-defined domain ontology + 6 external vocabularies followed at schema/mapping level |
| Taxonomies | 4 | 1 existing 35-topic taxonomy + 3 additional taxonomies derived from the pinned catalog |
| Controlled code lists | 12 | 12 project-defined code lists; no external code-list data imported |
| Standards/specification groups | 6 | Followed or applied in v1; no proposed-only or future-only items counted |

An ontology/vocabulary, taxonomy, controlled code list and standard are different
kinds of resources. Their counts are reported separately and must not be added
together into one total.

A resource is not considered implemented merely because it is mentioned here.
Implementation requires a defined schema use, documented source boundary and,
where applicable, validation tests.


## 2. Picture

```text
                                  (Topic) ◄── IN_TOPIC ──┐
                                                        │
(Venue) ◄── APPEARED_AT ── (Paper) ◄── CITES ── (Problem)
                              │                         │
                       AUTHORED_BY                     ├── RESTS_ON ──► (Concept) ── GENERALIZES ──► (Concept)
                              ▼                         │
                          (Person)                      ├── HAS_BOUND ──► (Bound) ── IN_MODEL ──► (ComputationModel)
                              │                         │
                       AFFILIATED_WITH                  ├── STATE_OF_ART ──► (Algorithm | System)
                              ▼                         │
                        (Institution)                   ├── HAS_GAP ──► (Gap)
                              │                         │
                         ACTIVE_ON                      ├── HAS_RESEARCH ──► (ResearchDirection)
                              └──────────────► (Problem)│
                                                        ├── CLOSING_REQUIRES ──► (FutureDirection)
                                                        │
                                                        ├── FROM_SOURCE ──► (DataSource)
                                                        │
                                                        └── CLASSIFIED_AS ──► (TaxonomyTerm)
                                                                                  ▲
(TaxonomyScheme) ── HAS_TERM ────────────────────────────────────────────────────┤
                                                                                  │
(TaxonomyTerm) ── BROADER_THAN ──► (TaxonomyTerm)
```

`Problem` is the centre of the graph. Each arrow represents an edge type;
properties attached to an edge are stored on that relationship.

The original `GENERALIZES` edge represents the Concept hierarchy.
`BROADER_THAN` represents hierarchies inside the additional taxonomies.
`CLASSIFIED_AS` connects problems to terms in those taxonomies.
```

## 3. Ontologies, vocabularies and standards followed

The KG defines its own domain model for DBMS research. The following external
vocabularies and semantic models are followed selectively for interoperability.
This does not require importing external instance data.

| Resource | Intended use | Boundary |
|---|---|---|
| DBMS Research domain ontology | Problems, papers, concepts, bounds, gaps, people, systems and research directions | Project-defined |
| W3C PROV-O | Provenance concepts and source traceability | Map relevant properties; do not import external records |
| W3C SKOS | Taxonomy and concept hierarchy modeling | Apply broader/narrower concepts to project-defined terms |
| Dublin Core Terms | Descriptive metadata for research resources | Map relevant metadata fields |
| FOAF | Person and relationship vocabulary patterns | Mapping reference only |
| Schema.org | Scholarly articles, people and organizations | Mapping reference only |
| CiTO | Citation relationship semantics | Use only where supported by source data |

The six standards/specification groups targeted for v1 are:

1. PROV-O provenance conventions.
2. SKOS concept-scheme and hierarchy conventions.
3. RDF/RDFS/OWL semantic-model interoperability conventions.
4. Dublin Core metadata conventions, including ISO 15836 where applicable.
5. ISO 26324 DOI conventions, when DOI values already occur in the source.
6. ISO 8601 date conventions for dates represented in the graph.

The list above defines schema-level conventions, not external data imports.
A vocabulary mapping must not imply that an external record was fetched or that
a relationship absent from the source was verified.

The inventory in `docs/standards.md` is the canonical record of these resources,
their intended use and implementation status.

## 4. Taxonomies

The completed v1 graph targets four taxonomies.

### 4.1 Existing DBMS Research topic taxonomy

The source's `TAXONOMY.md` defines 35 topics. Preserve the existing topic names,
ordering and source meaning.

Each topic becomes a `Topic` node. Each problem has exactly one `IN_TOPIC`
relationship to its primary topic.

### 4.2 DBMS problem-type taxonomy

Build this taxonomy from the problem titles, statements and relevant sections
of the pinned catalog.

It should distinguish problem types evidenced by the catalog, such as query
processing, transaction management, concurrency control, recovery, storage,
indexing, query optimization, distributed databases and data models.

These examples are candidates, not a fixed externally imported vocabulary.
The final term list and hierarchy must be derived from the catalog, reviewed
for duplicates and recorded before the build.

### 4.3 Solution and technique-family taxonomy

Build this taxonomy from techniques explicitly discussed in the catalog's
problem pages, including their solution approaches, algorithms and systems
sections.

Candidate distinctions include algorithmic, data-structural, optimization,
approximation, distributed-protocol, concurrency-control, recovery,
learning-based and systems-architecture approaches.

Only retain categories supported by the source. Do not infer that a technique
solves a problem merely because the terms appear together.

### 4.4 Computational-model and workload taxonomy

Build this taxonomy from computational models and workload assumptions
described in the catalog's bound and problem sections.

Candidate distinctions include centralized, distributed, parallel, streaming,
online, offline, randomized, deterministic and external-memory settings.

The final terms must be supported by source text. Unknown or absent information
must remain unclassified rather than being guessed.

### Taxonomy construction rules

- The three additional taxonomies must be built exclusively from the pinned
  catalog's content.
- Record each taxonomy's term definitions, parent-child hierarchy and
  classification rules in the implementation documentation.
- Every classification must have traceable provenance back to the source page.
- A problem may belong to multiple terms within a taxonomy when the source
  supports multiple classifications.
- A classification must not be based solely on a paper's title, author name
  or citation relationship unless the documented rule explicitly supports it.
- Keep the original `IN_TOPIC` relationship for compatibility with existing
  queries.
- Use `CLASSIFIED_AS` for assignments to terms in the three additional
  taxonomies.
- Do not claim the three additional taxonomies are complete until all source
  pages have been processed and classification coverage has been measured.

## 5. Node labels (17 planned)

The original 12 node labels are retained. Three domain labels from v0.1
(`Gap`, `ResearchDirection`, `DataSource`) remain, and two taxonomy labels
(`TaxonomyScheme`, `TaxonomyTerm`) are added.

| Label | One node per | Key properties | Source |
|---|---|---|---|
| `Problem` | Problem page | `id`, `title`, `slug`, `status`, `statement`, `problem_type`, `worked_example`, `first_added`, `last_reviewed`, `last_substantive_update`, `refs_checked`, `refs_unverified`, `catalog_provenance` | Header, §1, §10 |
| `Topic` | Existing topic | `id`, `number`, `name`, `slug`, `scope` | `TAXONOMY.md` |
| `Paper` | Deduplicated cited work | `id`, `title`, `year` (integer), `doi`, `arxiv_id`, `dblp_key`, `url`, `venue_raw`, `authors_raw` | §9 |
| `Person` | Author or named researcher | `id`, `name`, `name_form`, `dblp_pid`, `orcid`, `aliases` | §9 authors, §7 |
| `Venue` | Normalized venue name | `id`, `name`, `kind` | §9 |
| `Institution` | Institution on a checked list | `id`, `name`, `kind` | §7; source-derived names |
| `Concept` | Mathematical or systems concept on a checked list | `id`, `name`, `aliases` | §2 |
| `Algorithm` | Named algorithm | `id`, `name`, `family` | §3 |
| `System` | Named database system | `id`, `name`, `kind`, `family` | §3 |
| `Bound` | Upper or lower bound of one problem | `id`, `direction`, `kind`, `text` | §4, §5 |
| `ComputationModel` | Computational model described by a bound | `id`, `name`, `class` | §4, §5 |
| `Gap` | Gap section of a problem | `id`, `text`, `verdict`, `verdict_raw`, `verdict_method` | §6 |
| `ResearchDirection` | Item in a problem's research section | `id`, `text`, `frontier` | §7 |
| `FutureDirection` | Future-work bullet | `id`, `text` | §8 |
| `DataSource` | Pinned source catalog | `id`, `name`, `url`, `version`, `licence` | Source lock file |
| `TaxonomyScheme` | One of the four taxonomies | `id`, `name`, `description`, `source_rule`, `version` | Source-derived taxonomy definitions |
| `TaxonomyTerm` | Term in one of the three additional taxonomies | `id`, `taxonomy_id`, `name`, `slug`, `definition` | Derived from catalog pages |

`Topic` represents terms in the existing primary taxonomy. `TaxonomyTerm`
represents terms in the three additional taxonomies. `TaxonomyScheme` makes
the four schemes explicit in the graph.

The taxonomy scheme nodes and terms must be created from the project-defined
taxonomy specifications. No external taxonomy records or term assignments
may be imported.

### 5.1 New taxonomy properties and assignments

`Problem.problem_type` is a controlled classification from the DBMS
problem-type taxonomy. It is optional when the source does not support a
reliable classification. The `CLASSIFIED_AS` edge is authoritative for
taxonomy assignments; if the property is stored for query convenience, it
must agree with those edges.

`Algorithm.family` and `System.family` use the project-defined technique-family
vocabulary when the catalog provides sufficient evidence. Missing evidence
must remain unclassified.

`ComputationModel.class` uses the computational-model/workload vocabulary.
Its value must be supported by the source text describing the model.

For the additional taxonomies, `CLASSIFIED_AS.evidence_status` records the
basis of the assignment. The allowed values are defined in §8.

## 6. Stable identifiers

IDs must be deterministic so that rebuilding from the same pinned source
produces the same identifiers.

| Entity | ID rule |
|---|---|
| Problem | `problem:<NN-topic>/<slug>` |
| Topic | `topic:<NN-slug>` |
| Paper | `paper:doi:<doi>`; otherwise `paper:arxiv:<id>`; otherwise `paper:t:<title-hash>` |
| Person | `person:dblp:<pid>` when source-resolved; otherwise `person:<slug>` |
| Venue | `venue:<slug>` |
| Institution | `institution:<key>` |
| Concept | `concept:<key>` |
| Bound | `<problem-id>#bound-upper` or `<problem-id>#bound-lower` |
| Gap | `<problem-id>#gap` |
| ResearchDirection | `<problem-id>#research-<position>` |
| FutureDirection | `<problem-id>#future-<position>` |
| TaxonomyScheme | `taxonomy:<slug>` |
| TaxonomyTerm | `taxonomy:<taxonomy-slug>:<term-slug>` |
| DataSource | `source:dbms-research:<commit>` |

### 6.1 Paper title hash

`paper:t:` uses the first 12 hexadecimal characters of the SHA-1 hash of the
normalized title.

Normalization:
1. Unicode NFKC.
2. Case-fold.
3. Remove catalog Markdown emphasis markers (`*`, `_`).
4. Replace every non-letter and non-digit character with a space.
5. Collapse repeated spaces.
6. Trim leading and trailing spaces.

A genuine title wording change may produce a different ID; that limitation
is accepted and should be documented.

### 6.2 Person ID limitations

Before any permitted resolution, `person:<slug>` uses the written name in
lowercase with non-letters replaced by hyphens.

This can split one person represented in multiple ways and merge distinct
people who share the same written name. `Person.name_form` distinguishes
full names, initials and surnames so queries can exclude ambiguous records.

No external DBLP lookup or enrichment is performed in v1. DBLP identifiers
may be retained only when already present in the pinned catalog.

## 7. Edge types (19 planned)

The 16 edge types from v0.1 are retained. Three taxonomy relationships are
added: `HAS_TERM`, `BROADER_THAN` and `CLASSIFIED_AS`.

| Edge | From → To | Properties | Meaning |
|---|---|---|---|
| `IN_TOPIC` | Problem → Topic | — | Primary topic of the problem |
| `CITES` | Problem → Paper | `role`, `role_raw`, `position`, `verified` | Paper listed in §9 |
| `AUTHORED_BY` | Paper → Person | `position` | Authorship as written in the source |
| `APPEARED_AT` | Paper → Venue | — | Venue associated with the paper |
| `RESTS_ON` | Problem → Concept | — | Concept used by §2 |
| `GENERALIZES` | Concept → Concept | — | Broader concept to narrower concept |
| `HAS_BOUND` | Problem → Bound | `direction` | Best-known bound recorded for the problem |
| `IN_MODEL` | Bound → ComputationModel | — | Model in which the bound holds |
| `STATE_OF_ART` | Problem → Algorithm or System | `kind` | Named algorithm/system in §3 |
| `HAS_GAP` | Problem → Gap | — | Gap described in §6 |
| `HAS_RESEARCH` | Problem → ResearchDirection | `position` | Research direction in §7 |
| `CLOSING_REQUIRES` | Problem → FutureDirection | `position` | Future-work bullet in §8 |
| `ACTIVE_ON` | Person or Institution → Problem | `direction` | Named in §7; naming does not verify activity |
| `AFFILIATED_WITH` | Person → Institution | — | Affiliation only if present in source data |
| `RELATED_TO` | Problem → Problem | `method`, `score` | Computed relationship; see source restrictions |
| `FROM_SOURCE` | Problem → DataSource | — | Problem originates from pinned catalog |
| `HAS_TERM` | TaxonomyScheme → Topic or TaxonomyTerm | — | Term belongs to taxonomy scheme |
| `BROADER_THAN` | Topic or TaxonomyTerm → Topic or TaxonomyTerm | — | Broader term to narrower term within the same taxonomy |
| `CLASSIFIED_AS` | Problem → TaxonomyTerm | `evidence_status`, `method` | Source-supported assignment to an additional taxonomy |

`HAS_TERM` must connect a term to the correct taxonomy scheme.
`BROADER_THAN` must not connect terms from different taxonomies.
`CLASSIFIED_AS` must point to a term in one of the three additional taxonomies.

The existing `GENERALIZES` relationship remains for the mathematical and
systems `Concept` hierarchy. It is not a substitute for taxonomy hierarchy
edges.

### 7.1 Relationship generation restrictions

- Source-derived relationships must be traceable to source pages.
- `RELATED_TO` is a computed relationship, not an externally sourced fact.
  Its method and score must be documented and reproducible.
- Do not create `AFFILIATED_WITH` edges from external DBLP data in v1.
- Do not infer authorship, affiliations, citation roles or research activity
  when the pinned source does not support them.

## 8. Provenance and source integrity

Every node must carry provenance metadata sufficient to trace its origin.

| Field | Meaning | Requirement |
|---|---|---|
| `provenance` | `real` for source-backed content or a documented derived record | Required |
| `source` | `dbms_research` for source-derived records | Required |
| `method` | `parsed`, `list-matched`, `keyword-classified` or `computed`, as applicable | Required |
| `retrieved_at` | Fetch date recorded by the source lock file | Required |
| `source_date` | Pinned source commit date | Required |
| `source_url` | URL of the exact pinned source file or page | Required for page-derived records |
| `page_count` | Number of source pages naming a merged shared entity | Required for merged shared entities |
| `enriched_by` | Additional source identifiers, if enrichment is ever authorized | Absent in v1 unless source evidence warrants it |

For a shared entity merged across multiple pages, `source_url` identifies the
first source page in deterministic ID order and `page_count` records how many
pages name it. Its relationships back to Problems provide the graph-level
traceability.

For project-defined taxonomy terms, include the source pages and deterministic
classification method used to derive the term. If multiple source pages
support a term, retain sufficient evidence to reproduce the term and its
assignments.

For computed records, such as `RELATED_TO`, record the computation method
and the inputs used. Do not label computed relationships as explicitly stated
by the source.

The `DataSource` node records the pinned catalog's name, URL, commit and
licence. The source lock file must preserve the exact commit used to build v1.

## 9. Controlled code lists (12 planned)

A controlled code list defines allowed values for a graph property. The
following twelve lists are project-defined. External identifiers such as DOI,
arXiv IDs and ORCID IDs are not counted as project-defined code lists.

### Existing code lists (8)

| # | Property | Allowed values | Source / rule |
|---:|---|---|---|
| 1 | `Problem.status` | `open`, `partially-solved`, `empirically-open`, `solved-but-impractical`, `stale` | Preserve source status. `stale` is allowed by the template but currently unused |
| 2 | `CITES.role` | `foundational`, `sota`, `survey`, `systems`, `docs`, `artifact`, `attack` | Preserve the source's bold tag in §9; retain raw value |
| 3 | `Gap.verdict` | `open`, `partially-solved`, `empirically-open`, `closed`, `unstated` | Explicit verdict first; documented keyword rule second |
| 4 | `Bound.kind` | `time`, `space`, `impossibility` | Classify from bound section using a documented rule |
| 5 | `STATE_OF_ART.kind` | `theory`, `systems` | Classify from the source section and named entity |
| 6 | `Person.name_form` | `full`, `initials`, `surname` | Determined from the written name |
| 7 | `Venue.kind` | `conference`, `journal`, `preprint`, `other` | Determined from source information and project rules |
| 8 | `Institution.kind` | `academic`, `industry`, `government`, `non-profit` | Only for institutions accepted by the checked list |

### New code lists (4)

| # | Property | Allowed values | Source / rule |
|---:|---|---|---|
| 9 | `Problem.problem_type` | Project-defined DBMS problem-type taxonomy term IDs | Derive terms and assignments from catalog pages; do not import external classifications |
| 10 | `Algorithm.family` and `System.family` | Project-defined technique-family taxonomy term IDs | Use only where source evidence supports the assignment |
| 11 | `ComputationModel.class` | Project-defined computational-model/workload taxonomy term IDs | Derive from model assumptions in the source |
| 12 | `CLASSIFIED_AS.evidence_status` | `explicit-in-source`, `rule-classified`, `unresolved` | Record whether the classification is explicitly supported, assigned by a documented rule, or unresolved |

The allowed values of lists 9–11 are the term IDs in the corresponding
catalog-derived taxonomy, not a second independent vocabulary. The term
inventory and its classification rules must be versioned with the schema.

`evidence_status` means:
- `explicit-in-source`: the source directly supports the classification.
- `rule-classified`: a documented and reproducible rule assigned the category.
- `unresolved`: the available source text does not support a reliable category.

Do not assign a default category to missing or ambiguous evidence.

### 9.1 Gap verdict classification

`Gap.verdict` uses two steps:

1. `stated`: use the bold phrase that opens §6, when present.
2. `keyword`: apply a documented keyword rule over the whole §6 text when
   no explicit verdict is present.

Examples of candidate keywords include `closed`, `tight`, `open` and `unknown`.
Rules must account for negation and context. Anything the rule cannot classify
remains `unstated`.

`Gap.verdict_method` records `stated`, `keyword` or `none`. Measure the number
of records classified by each method after the build.

### 9.2 Code-list validation

For every code list:
- Reject values outside its allowed set.
- Preserve the raw source value where normalization changes meaning or spelling.
- Record the method used for inferred classifications.
- Test missing and ambiguous values explicitly.
- Ensure every taxonomy term ID references a term in the correct taxonomy.
- Report value frequencies and unresolved counts after the build.

## 10. Schema changes from the old graph

The v1 design retains the original graph while addressing these issues:

| # | Old graph issue | Planned fix |
|---:|---|---|
| 1 | Gap information from §6 missing | `Gap` nodes and `HAS_GAP` edges |
| 2 | §7 retained people but lost research directions | `ResearchDirection` nodes and `HAS_RESEARCH` |
| 3 | Problem header dates missing | Store dates on `Problem` |
| 4 | Citation role stored on Paper | Store role on `CITES` |
| 5 | Paper year stored as text | Store year as integer |
| 6 | Paper URL used without separated identifiers | Separate DOI, arXiv ID and DBLP key when source-provided |
| 7 | Institution list included non-institutions | Use a checked institution list |
| 8 | Algorithm list included citation strings | Only create named algorithm nodes |
| 9 | Concept hierarchy too thin | Expand the checked concept list and hierarchy |
| 10 | Edge properties used generic `prop` | Give each edge property a specific meaning |
| 11 | Counter-based IDs changed on rebuild | Deterministic IDs based on content and source identity |
| 12 | No provenance fields | Add provenance to all nodes |
| 13 | Only one taxonomy represented | Add three source-derived taxonomies |
| 14 | Taxonomy terms and hierarchy were not explicit | Add `TaxonomyScheme`, `TaxonomyTerm`, `HAS_TERM`, `BROADER_THAN` and `CLASSIFIED_AS` |
| 15 | Classification rules were not consistently represented | Add four code lists and validation tests |

## 11. Source-catalog limitations

The source catalog has known limitations that must not be silently repaired using
external data:

- The `Worked Example` section appears in pages but is absent from the source
  template; preserve the source content.
- The `Systems` and `Attack` reference tags occur in pages although they are
  missing from the source template.
- The documentation counts in `USING_WITH_SAMYAMA_GRAPH.md` do not all match
  the pinned snapshot.
- Only 140 of 1,053 pages have a bold opening phrase in §6.
- The source template allows `stale`, but no source page currently uses it.
- Page review dates are unevenly distributed.
- Research-direction and future-work text may be duplicated or expressed
  differently across pages.

Record these as source limitations. Do not invent missing facts or update the
source catalog as part of this KG build.

## 12. Question coverage

The 48 questions in [`scope.md`](scope.md) remain the acceptance target.

| Scope group | Questions | Main schema support |
|---|---|---|
| A. Problems and topics | 1–6 | Problem, Topic, IN_TOPIC |
| B. One problem | 7–15 | Problem, CITES, Bound, Gap, ResearchDirection, FutureDirection |
| C. Papers | 16–22 | Paper, CITES, Venue |
| D. People and institutions | 23–28 | Person, AUTHORED_BY, ACTIVE_ON, AFFILIATED_WITH, Institution |
| E. Algorithms, systems and bounds | 29–34 | STATE_OF_ART, Bound, ComputationModel, Gap |
| F. Connections | 35–40 | RELATED_TO, Concept, RESTS_ON, GENERALIZES, taxonomy classifications |
| G. Opportunities | 41–45 | Gap, ACTIVE_ON, FutureDirection, Paper.year |
| H. Should not answer | 46–48 | No global citation counts, post-pinned-date status or funding claims |

Q34 remains partly answerable: `Gap.verdict` can classify gap status but does
not compare bounds. Q41 remains partly answerable: open problems can be listed
by verdict, but gap width cannot be reliably measured from prose alone.

Groups F and G must be re-tested against the implemented schema; additional
taxonomies improve classification but do not automatically resolve every
question.

## 13. Build acceptance criteria

The implementation is accepted only when all of the following are verified.

### Source integrity
- [ ] The build uses the exact pinned commit.
- [ ] All graph instance data originates from the pinned catalog.
- [ ] No external API enrichment, external taxonomy records or external
      bibliographic records were imported.
- [ ] Source attribution and licence metadata are retained.

### Schema
- [ ] The implementation has 17 planned node labels and 19 planned edge types,
      or any deviation is explicitly documented and approved.
- [ ] The four taxonomies are represented and have terms derived from the
      pinned catalog.
- [ ] All twelve controlled code lists have explicit allowed values.
- [ ] Every taxonomy assignment has traceable provenance.
- [ ] Stable IDs produce the same identifiers for repeat builds of the same
      source commit.

### Inventory
- [ ] Ontology/vocabulary inventory: 7 documented entries.
- [ ] Taxonomy inventory: 4 implemented schemes.
- [ ] Controlled code-list inventory: 12 implemented lists.
- [ ] Standards/specification inventory: 6 documented and applied groups.
- [ ] No proposed-only or future-only resource is included in the completed
      implementation counts.
- [ ] Each counted resource has evidence of actual schema use or validation.

### Graph quality
- [ ] Every problem has exactly one primary `IN_TOPIC` edge.
- [ ] Taxonomy hierarchy edges remain within their own taxonomy.
- [ ] `CLASSIFIED_AS` edges point to valid taxonomy terms.
- [ ] Code-list values pass validation.
- [ ] Provenance and stable-ID tests pass.
- [ ] The build reports actual node, edge, label, edge-type, taxonomy-term
      and classification counts.
- [ ] Scope questions are tested, including the documented limitations of
      Q34 and Q41.

## 14. Decisions for v1

1. Build from the pinned DBMS Research catalog only.
2. Do not perform DBLP lookups or other external data enrichment.
3. Do not import external taxonomy terms, ontology instances or metadata.
4. Use external vocabularies and standards only as documented modeling and
   interoperability references.
5. Build the three additional taxonomies from catalog evidence and record
   the derivation rules.
6. Keep the original 35-topic taxonomy and its `IN_TOPIC` relationship.
7. Include all v1 code lists and validation rules in the initial implementation.
8. Do not count planned resources as implemented until the build and tests
   verify them.
