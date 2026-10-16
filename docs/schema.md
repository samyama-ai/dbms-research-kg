# DBMS Research KG — Design Notes

The labelled property graph: what each label and edge holds, how many there are, and why it is
shaped this way. The concepts behind it are in [`ontology.md`](ontology.md), the coded values in
[`taxonomy.md`](taxonomy.md), and the machine-checked version in
[`../schema/conformance.json`](../schema/conformance.json) (schema version 1.1.0). The
engine indexes are in [`../schema/dbms_research_kg.cypher`](../schema/dbms_research_kg.cypher).

| | |
|---|---|
| Graph model | labelled property graph, openCypher, Samyama Graph |
| Source | `github.com/samyama-ai/dbms_research` at `5fff7f74508a52ac238f3bb608b8c8c872489fec` (2026-09-09), 1,053 pages, CC BY 4.0 |
| Size | 20,211 nodes, 53,721 edges; 16 labels, 17 relationship types |
| Questions | the 48 of [`scope.md`](../benchmarks/scope.md), run in [`../benchmarks`](../benchmarks/README.md) |
| Sibling KG | AI Research KG: the same edge names where the meaning is the same |

## Picture

```
                             (Topic)◄──IN_TOPIC──┐
                                                 │
(Venue)◄──APPEARED_AT──(Paper)◄──CITES {role}──(Problem)──RESTS_ON──►(Concept)──GENERALIZES──►(Concept)
                         │                       │ │ │ │
                  AUTHORED_BY {position}         │ │ │ ├──HAS_BOUND {direction}──►(Bound)──IN_MODEL──►(ComputationModel)
                         ▼                       │ │ │ ├──STATE_OF_ART {kind}──►(Algorithm | System)
(Institution)◄──AFFILIATED_WITH──(Person)        │ │ │ ├──HAS_GAP──►(Gap)
                                   │             │ │ │ ├──HAS_RESEARCH──►(ResearchDirection)
                                   └─ACTIVE_ON───┘ │ │ └──CLOSING_REQUIRES──►(FutureDirection)
(Institution)──ACTIVE_ON {direction}───────────────┘ ├──RELATED_TO {method, score}──►(Problem)   [computed]
                                                     └──FROM_SOURCE──►(DataSource)
(Problem | Algorithm | System | ComputationModel)──CLASSIFIED_AS {evidence_status}──►(TaxonomyTerm)
```

Problem is the centre. Each arrow is one edge type; properties in `{braces}` sit on the edge.

## Node labels (16)

Every node also carries `id`, `provenance`, `source`, `method`, `retrieved_at`, `source_date` and
`source_url`; nodes shared across pages also carry `page_count`, and list-matched nodes the
`extraction` that found them. Those are left out of the table.

| Label | Count | One node per | Properties |
|---|---:|---|---|
| `Person` | 4,454 | one written author or researcher name | `name`, `name_form`; optional `dblp_pid`, `orcid`, `aliases` |
| `FutureDirection` | 3,825 | one bullet of §8 | `problem_id`, `text` |
| `Paper` | 2,679 | one cited work, merged across pages | `citation_text`, `parse_status`; optional `title`, `year`, `doi`, `arxiv_id`, `dblp_key`, `url`, `venue_raw`, `authors_raw`, `authors`, `source_verified` |
| `ResearchDirection` | 2,496 | one item of §7 | `problem_id`, `text`, `frontier` |
| `Bound` | 2,106 | the upper or the lower bound of one problem | `problem_id`, `direction`, `kind`, `text` |
| `Problem` | 1,053 | one problem page | `title`, `slug`, `status`, `statement`, `worked_example`; optional `first_added`, `last_reviewed`, `last_substantive_update`, `stale_since`, `refs_checked`, `refs_unverified`, `catalog_provenance`, `problem_type`, `classification_evidence_status`, `topic_id`, `problem_statement`, `mathematical_foundations`, `state_of_the_art`, `upper_bound_text`, `lower_bound_text`, `gap_text`, `current_research`, `future_work_text`, `key_references`, `problem_type_method` |
| `Gap` | 1,053 | §6 of one problem | `problem_id`, `text`, `verdict`, `verdict_raw`, `verdict_method` |
| `System` | 982 | one system named in §3 | `name`, `kind`, `family`; optional `family_method`, `family_evidence` |
| `Venue` | 677 | one normalised venue name | `name`, `kind` |
| `Algorithm` | 585 | one algorithm named in §3 | `name`, `family`; optional `family_method`, `family_evidence` |
| `Concept` | 90 | one idea on the concept list, found in §2 | `name`; optional `aliases` |
| `Institution` | 82 | one name on the checked list | `name`, `kind` |
| `TaxonomyTerm` | 77 | one code of one taxonomy | `scheme`, `code`, `name`, `notation` |
| `Topic` | 35 | one row of `TAXONOMY.md` | `number`, `name`, `slug`; optional `scope` |
| `ComputationModel` | 16 | one model on the list, found in §4/§5 | `name`, `class` |
| `DataSource` | 1 | the catalog at the pinned commit | `name`, `url`, `version`, `licence` |

## Edge types (17)

Every edge also carries `source` and `source_url`.

| Edge | From → To | Count | Properties | Meaning |
|---|---|---:|---|---|
| `RELATED_TO` | Problem → Problem | 8,686 | `score`, `shared_evidence_count`; optional `shared_papers`, `shared_concepts`, `source_commit`, `source_urls` | computed: shared papers and concepts, Jaccard score |
| `AUTHORED_BY` | Paper → Person | 7,000 | `position` | authorship as written, first author = 1 |
| `CITES` | Problem → Paper | 6,157 | `role`, `position`, `verification_status`, `cito_property`; optional `role_raw`, `role_status`, `artifact_kind`, `cito_mapping_note` | the page lists the paper in §9 |
| `ACTIVE_ON` | Person, Institution → Problem | 5,536 | `direction` | named in §7: naming, not verified activity |
| `STATE_OF_ART` | Problem → Algorithm, System | 4,058 | `kind` | named in §3 |
| `CLOSING_REQUIRES` | Problem → FutureDirection | 3,825 | `position` | a bullet of §8 |
| `CLASSIFIED_AS` | Problem, Algorithm, System, ComputationModel → TaxonomyTerm | 3,689 | `evidence_status`, `evidence` | a taxonomy code, with its evidence |
| `APPEARED_AT` | Paper → Venue | 2,609 | — | where the paper appeared |
| `HAS_RESEARCH` | Problem → ResearchDirection | 2,496 | `position` | an item of §7 |
| `HAS_BOUND` | Problem → Bound | 2,106 | `direction` | the best-known bound |
| `RESTS_ON` | Problem → Concept | 1,987 | — | §2 uses the concept |
| `IN_MODEL` | Bound → ComputationModel | 1,953 | — | the model the bound holds in |
| `IN_TOPIC` | Problem → Topic | 1,053 | — | the page's topic |
| `HAS_GAP` | Problem → Gap | 1,053 | — | §6 |
| `FROM_SOURCE` | Problem → DataSource | 1,053 | — | the pinned commit |
| `AFFILIATED_WITH` | Person → Institution | 429 | `evidence` | a §7 bracket; what the page states |
| `GENERALIZES` | Concept → Concept | 31 | `rationale` | broader concept to narrower, reviewed |

## Design decisions

**Problem is the centre, and each section of its page is a node.** The gap (§6), current research
(§7) and future work (§8) are nodes of their own, so a question such as "which open problems have
a closed gap" or "who works on this" is a pattern, not a text search.

**Edge properties have names.** `CITES.role`, `HAS_BOUND.direction`, `STATE_OF_ART.kind`,
`AUTHORED_BY.position`: one meaning each. The 2026-09 graph called them all `prop`.

**A rule's output says it is a rule.** Problem type, technique family, model class and gap verdict
are ours, so each records its method and evidence (see [`taxonomy.md`](taxonomy.md)).

**Names are not merged.** A Person is a written name. Merging "T. Neumann" with "Thomas Neumann"
would be a guess; the graph keeps `name_form` instead, so a query can be careful.

**Paper identity is the citation's.** Two citations are one paper when a DOI, an arXiv id (without
version), a DBLP key, or the title and year agree, and no identifiers conflict. The id hashes the
work's representative citation (the parsed one with a title, then a year, then the most
identifiers), so it is stable for the pinned commit.

**Taxonomy codes are nodes.** TaxonomyTerm makes each scheme queryable as SKOS concepts. They are
schema vocabulary (`provenance = schema-vocabulary`, `source = project_schema`), not catalog facts.

**Nothing from outside.** No DBLP, ORCID, embeddings or citation counts in this build. `Person.dblp_pid`
and `orcid` are declared for a later enrichment step and are absent.

## Differences from the 2026-09 graph

The graph published before this one (`dbms-research.sgsnap`, kg-snapshots-v10: 12 labels, 13 edge
types, 20,019 nodes, 39,393 edges), and what this schema changes:

| # | 2026-09 graph | This graph | Questions |
|---|---|---|---|
| 1 | §6 The Gap missing | Gap node with a verdict | 11, 34, 41 |
| 2 | §7 kept only as person names | ResearchDirection; ACTIVE_ON from labs too, with the direction | 13 |
| 3 | header dates missing | on Problem | 6 |
| 4 | reference role on the Paper | role on CITES | 9, 18 |
| 5 | year stored as text | integer | 19, 45 |
| 6 | one `url`, no identifiers | `doi`, `arxiv_id`, `dblp_key` | 21 |
| 7 | Institution held surnames and topics | a checked list | 27 |
| 8 | Algorithm held citations | citations dropped | 29 |
| 9 | 34 concepts, 1 GENERALIZES | 90 concepts, 31 reviewed pairs | 37, 38 |
| 10 | edge properties all called `prop` | named properties | all edge questions |
| 11 | counter ids (`paper:0`) | ids from content | rebuilds |
| 12 | no provenance | provenance on every node and edge | trust |
| 13 | no taxonomy codes | TaxonomyTerm and CLASSIFIED_AS | 1–5, 29–33 |

Four labels hold fewer nodes than in 2026-09, each because of a fix: Paper (citations merged by
identity), Person (one author list per paper), Institution (only the checked list) and Algorithm
(citations dropped). The [quality report](../benchmarks/quality-report.md) gives the figures.

## Question coverage

| Scope group | Questions | Answered through |
|---|---|---|
| A Problems and topics | 1–6 | Problem, Topic, IN_TOPIC |
| B One problem | 7–15 | Problem, CITES, Bound, Gap, ResearchDirection, ACTIVE_ON, FutureDirection |
| C Papers | 16–22 | Paper, CITES, Venue |
| D People and institutions | 23–28 | Person, AUTHORED_BY, ACTIVE_ON, AFFILIATED_WITH, Institution |
| E Algorithms, systems, bounds | 29–34 | STATE_OF_ART, Bound, ComputationModel, Gap. Q34 only from `Gap.verdict`, not by comparing bounds |
| F Connections | 35–40 | RELATED_TO, Concept, RESTS_ON, GENERALIZES. Q39 needs vector search |
| G Opportunities | 41–45 | Gap, ACTIVE_ON, FutureDirection, `Paper.year`. Q41 lists by verdict; the width of a gap is not measurable from prose |
| H Should not answer | 46–48 | nothing: no global citation counts, no status after the pinned commit, no funding |

## Open for review

1. The project taxonomies, crosswalks, institution list and concept hierarchy are our rules. They
   need a reviewer's approval before a production load.
2. Should the catalog issues found while reading it (the Worked Example section and the `[Systems]` and
   `[Attack]` tags missing from its template) be raised on `samyama-ai/dbms_research`?
