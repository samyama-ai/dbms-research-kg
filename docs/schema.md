# DBMS Research KG — Schema (v0.1, plan)

This is the **plan** for the graph, written in Phase 1 before any code. It says which node
types and edge types the graph will have, which section of a problem page each one comes
from, and how it differs from the existing graph. Phase 3 builds it; the numbers then get
measured and this file becomes "as built".

| | |
|---|---|
| Version | v0.1 plan (2026-10-14) |
| Graph model | labelled property graph, openCypher (Samyama Graph 1.11.0) |
| Source | `github.com/samyama-ai/dbms_research`, pinned at `5fff7f74508a52ac238f3bb608b8c8c872489fec` (2026-09-09), 1,053 pages, licence CC BY 4.0 |
| Data pin | Until the Phase 2 download script exists, **this table is the committed record of the pinned commit**. The lock file `data/dbms_research.lock.json` is git-ignored and exists only on the machine that fetched the data. |
| Old graph | `dbms-research.sgsnap`, kg-snapshots-v10, iteration 2026-09: 12 labels, 13 edge types, 20,019 nodes, 39,393 edges |
| Questions | [scope.md](scope.md), 48 questions; §7 below maps them to this schema |
| Sibling KG | AI Research KG: same edge names where the meaning is the same |

## 1. Picture

```
                             (Topic)◄──IN_TOPIC──┐
                                                 │
(Venue)◄──APPEARED_AT──(Paper)◄──CITES {role}──(Problem)──RESTS_ON──►(Concept)──GENERALIZES──►(Concept)
                         │                       │ │ │ │
                  AUTHORED_BY {position}         │ │ │ ├──HAS_BOUND {direction}──►(Bound)──IN_MODEL──►(ComputationModel)
                         ▼                       │ │ │ ├──STATE_OF_ART {kind}──►(Algorithm | System)
(Institution)◄──AFFILIATED_WITH──(Person)        │ │ │ ├──HAS_GAP──►(Gap)                              NEW
                                   │             │ │ │ ├──HAS_RESEARCH──►(ResearchDirection)           NEW
                                   └─ACTIVE_ON───┘ │ │ └──CLOSING_REQUIRES──►(FutureDirection)
(Institution)──ACTIVE_ON {direction}───────────────┘ ├──RELATED_TO {method, score}──►(Problem)   [computed]
                                                     └──FROM_SOURCE──►(DataSource)                NEW
```

Problem is the centre. Each arrow is one edge type; properties in `{braces}` sit on the edge.

## 2. Node labels (15)

Every node also carries the provenance fields of §4. "Old count" is the 2026-09 graph, for
comparison. "From" is the part of the page the node is read from.

| Label | One node per | Key properties | From | Old count | Change |
|---|---|---|---|---:|---|
| `Problem` | problem page | `id`, `title`, `slug`, `status`, `statement`, `worked_example`, `first_added`, `last_reviewed`, `last_substantive_update`, `refs_checked`, `refs_unverified`, `catalog_provenance` | header + §1 + §10 | 1,053 | header dates added; `worked_example` carried over from the old `workedExample` (renamed only) |
| `Topic` | row of TAXONOMY.md | `number`, `name`, `slug`, `scope` | TAXONOMY.md | 35 | `scope` added |
| `Paper` | cited work, deduplicated | `title`, `year` (**integer**), `doi`, `arxiv_id`, `dblp_key`, `url`, `venue_raw`, `authors_raw` | §9 | 2,962 | year as a number, identifiers split out, role moved to `CITES` |
| `Person` | author or named researcher | `name`, `name_form` (full / initials / surname), `dblp_pid`, `orcid`, `aliases` | §9 authors, §7 names | 5,193 | `name_form` added |
| `Venue` | normalised venue name | `name`, `kind` (conference / journal / preprint / other) | §9 | 480 | `kind` added |
| `Institution` | university, company or lab on a fixed list | `name`, `kind` (academic / industry / government / non-profit) | §7, DBLP affiliations | 1,407 | **only names on a checked list**, so no "Pavlo" or "learned optimizers" |
| `Concept` | mathematical or systems idea on a fixed list | `name`, `aliases` | §2 | 34 | **list grown** well beyond 34 |
| `Algorithm` | named algorithm | `name` | §3 | 2,808 | **citations such as "Yannakakis (1981)" no longer become algorithms** |
| `System` | named database system | `name`, `kind` | §3 | 108 | — |
| `Bound` | upper or lower bound section of one problem | `direction` (upper / lower), `kind` (time / space / impossibility), `text` | §4, §5 | 2,106 | `expr` renamed `text` |
| `ComputationModel` | model a bound holds in | `name` | §4, §5 | 8 | — |
| `Gap` | §6 of one problem | `text`, `verdict` (code list §5), `verdict_raw`, `verdict_method` (stated / keyword / none) | §6 | — | **new** |
| `ResearchDirection` | item of §7 of one problem | `text`, `frontier` (true when marked *(frontier — verify)*) | §7 | — | **new** |
| `FutureDirection` | bullet of §8 | `text` | §8 | 3,825 | — |
| `DataSource` | source catalog | `name`, `url`, `version` (pinned commit), `licence` | lock file | — | **new**, as in the AI KG |

**Ids** are made the same way on every build, so a rebuild gives the same ids:
`problem:<NN-topic>/<slug>`, `topic:<NN-slug>`, `paper:doi:<doi>` → `paper:arxiv:<id>` → `paper:t:<title hash>`,
`person:<slug>` (or `person:dblp:<pid>` once resolved), `venue:<slug>`, `institution:<key>`, `concept:<key>`,
`<problem id>#gap`, `<problem id>#research-N`, `<problem id>#future-N`, `<problem id>#bound-upper|lower`.
The old graph used counters (`paper:0`, `bound:0`), which change whenever the input changes.

**Title hash.** `paper:t:` is the first 12 hex characters of the SHA-1 of the normalised title. Normalisation, in this order: Unicode NFKC; case-fold; remove the catalog's markdown (`*`, `_`); replace every character that is not a letter or digit with a space; collapse runs of spaces; trim. So "*On the Desirability of Acyclic Database Schemes.*" and "on the desirability of acyclic database schemes" give the same id. A change of wording in the title still gives a new id; that is accepted.

**Person slug, known limits.** Before DBLP resolution, `person:<slug>` is the name as written, lower-cased, with non-letters replaced by `-`. This (a) **splits** one person written two ways ("M. Yannakakis" and "Mihalis Yannakakis", scope Q28) and (b) **merges** different people who share a written name (two "Y. Wang"s). Initials and bare surnames are flagged by `name_form` so queries can leave them out. DBLP resolution (decision 1 in §8) is what fixes both.

## 3. Edge types (16)

| Edge | From → To | Properties | Meaning | Change |
|---|---|---|---|---|
| `IN_TOPIC` | Problem → Topic | — | exactly one per problem | — |
| `CITES` | Problem → Paper | `role` (§5), `role_raw`, `position`, `verified` | the page lists the paper in §9 | **role moved here from Paper**; `prop` renamed |
| `AUTHORED_BY` | Paper → Person | `position` (1 = first author) | authorship as written | `prop` renamed `position`, counted from 1 |
| `APPEARED_AT` | Paper → Venue | — | where the paper appeared | old `prop` (the year) dropped; the year lives on Paper |
| `RESTS_ON` | Problem → Concept | — | the problem's §2 uses the concept | — |
| `GENERALIZES` | Concept → Concept | — | broader concept → narrower | **filled from the concept list**, old graph had 1 |
| `HAS_BOUND` | Problem → Bound | `direction` | the problem's best-known bound | `prop` renamed |
| `IN_MODEL` | Bound → ComputationModel | — | the model the bound holds in | — |
| `STATE_OF_ART` | Problem → Algorithm or System | `kind` (theory / systems) | named in §3 | `prop` renamed |
| `HAS_GAP` | Problem → Gap | — | §6 of the problem | **new** |
| `HAS_RESEARCH` | Problem → ResearchDirection | `position` | an item of §7 | **new** |
| `CLOSING_REQUIRES` | Problem → FutureDirection | `position` | a bullet of §8 | — |
| `ACTIVE_ON` | Person → Problem, Institution → Problem | `direction` (the §7 item it was named in) | the page names this person or lab in §7 (naming, not verified activity) | Institution added as a source; `direction` added |
| `AFFILIATED_WITH` | Person → Institution | — | from DBLP | — |
| `RELATED_TO` | Problem → Problem | `method`, `score` | **computed** from shared papers and concepts | old `prop` and `score` mixed; now one meaning each |
| `FROM_SOURCE` | Problem → DataSource | — | the pinned catalog version | **new** |

## 4. Provenance

Every node says where it came from, so a reader can check it. Same fields as the AI KG.

| Field | Value | On |
|---|---|---|
| `provenance` | `real` (read from a real source, not made up) | every node |
| `source` | `dbms_research`: where the node itself was read | every node |
| `enriched_by` | list of extra sources that filled fields on the node, e.g. `["dblp"]` when `dblp_pid` or `orcid` came from DBLP; absent when none. Edges that come only from DBLP (`AFFILIATED_WITH`) carry `source: dblp` on the edge | nodes enriched later |
| `method` | `parsed`, `list-matched` (Concept, Institution), `keyword-classified` (Gap verdict, Bound kind), `computed` (RELATED_TO) | every node |
| `retrieved_at` | the fetch date from `data/dbms_research.lock.json` | every node |
| `source_date` | the pinned commit's date, 2026-09-09 | every node |
| `source_url` | `https://github.com/samyama-ai/dbms_research/blob/<commit>/<file>` | every node read from one page (Problem, Bound, Gap, ResearchDirection, FutureDirection) |
| `source_url` + `page_count` | for nodes merged across pages (Paper, Person, Venue, Concept, Algorithm, System): `source_url` is the **first** page that names it, in id order, and `page_count` says how many pages name it. The full list is the node's edges back to Problems | shared nodes |
| — | Topic comes from `TAXONOMY.md`; Institution, ComputationModel and DataSource come from fixed lists; they carry `source_url` of that file or none | list-based nodes |

The old graph has none of these fields.

## 5. Code lists

A code list is a fixed set of allowed values for one property.

| Property | Values | How |
|---|---|---|
| `Problem.status` | open · partially-solved · empirically-open · solved-but-impractical (· stale, allowed by the template, used by no page) | header, as written |
| `CITES.role` | foundational · sota · survey · systems · docs · artifact · attack | the bold tag in §9; measured counts: Foundational 2,777, SOTA 2,633, Survey 676, Systems 11, Docs 5, Attack 2, Artifact 2 |
| `Gap.verdict` | open · partially-solved · empirically-open · closed · unstated | two steps. (1) **stated**: the bold phrase that opens §6; 140 of 1,053 pages have one, most of them verdicts such as "Open" or "Partially solved". (2) **keyword**: for the rest, a keyword rule over the whole §6 text (e.g. "closed", "tight", "bounds match" without a negation → closed; "open", "unknown" → open). Anything the rule can't place stays `unstated`. `verdict_method` records which step decided. The share of each step is measured in Phase 3, not promised here |
| `Bound.kind` | time · space · impossibility | as in the old graph |
| `STATE_OF_ART.kind` | theory · systems | as in the old graph |
| `Person.name_form` | full · initials · surname | shape of the name |
| `Venue.kind` | conference · journal · preprint · other | from a venue list |
| `Institution.kind` | academic · industry · government · non-profit | from the fixed list |

## 6. Differences from the 2026-09 graph

In short, what this schema fixes, with the scope questions each fix serves.

| # | Old graph | This schema | Questions |
|---|---|---|---|
| 1 | §6 The Gap missing | `Gap` node with a verdict | 11, 34, 41 |
| 2 | §7 kept only as person names | `ResearchDirection` nodes; `ACTIVE_ON` from labs too, with the direction | 13 |
| 3 | header dates missing | on Problem | 6 |
| 4 | reference role on the Paper | role on `CITES` | 9, 18 |
| 5 | year stored as text | integer | 19, 45 |
| 6 | one `url`, no identifiers | `doi`, `arxiv_id`, `dblp_key` | 21 |
| 7 | Institution has surnames and topics | fixed checked list | 27 |
| 8 | Algorithm has citations | citations dropped from Algorithm | 29 |
| 9 | 34 concepts, 1 GENERALIZES | larger list with a hierarchy | 37, 38 |
| 10 | edge properties all called `prop` | named properties | all edge questions |
| 11 | counter ids (`paper:0`) | stable ids from content | rebuilds |
| 12 | no provenance | §4 fields on every node | trust |

Not changed in v0.1: Person merging still relies on DBLP (Q28), shared future directions
(Q44) need a way to match similar texts, and vector search (Q39) waits for the engine fix
(samyama-graph#5).

## 7. Question coverage

| Scope group | Questions | Answered through |
|---|---|---|
| A Problems and topics | 1–6 | Problem, Topic, IN_TOPIC |
| B One problem | 7–15 | Problem, CITES, Bound, Gap, ResearchDirection, ACTIVE_ON, FutureDirection |
| C Papers | 16–22 | Paper, CITES, Venue |
| D People and institutions | 23–28 | Person, AUTHORED_BY, ACTIVE_ON, AFFILIATED_WITH, Institution |
| E Algorithms, systems, bounds | 29–34 | STATE_OF_ART, Bound, ComputationModel, Gap. **Q34 only partly:** from `Gap.verdict`, not by comparing bounds |
| F Connections | 35–40 | RELATED_TO, Concept, RESTS_ON, GENERALIZES |
| G Opportunities | 41–45 | Gap, ACTIVE_ON, FutureDirection, Paper.year. **Q41 only partly:** gap width isn't measurable from prose, so open problems can be listed by verdict but not ranked by width |
| H Should not answer | 46–48 | nothing: the graph holds no global citation counts, post-2026-09 status or funding |

## 8. Open decisions 

1. **DBLP lookups.** The old graph resolved people against DBLP. Build v1 from the catalog
   only first, as in the AI KG, and add DBLP as a second step? Proposed: yes.
2. **Embeddings.** The old graph has a 1,024-dim embedding on every Problem. Keep them, or
   leave them out until vector search works on imported snapshots? Proposed: leave out in v1.
3. **Concept list.** Who reviews the concept list and its hierarchy before it goes in?
4. **Catalog issues.** Should findings 12, 13 and 18–20 of the [Phase 1 log](phase1-log.md) be raised as issues on `samyama-ai/dbms_research`? They are: the "Worked Example" section missing from TEMPLATE.md, the §9 tags `[Systems]` and `[Attack]` missing from it, and three counts in USING_WITH_SAMYAMA_GRAPH.md that don't match the snapshot.
