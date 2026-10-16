# Ontology

What kinds of thing this graph holds, how they relate, what must always be true of them, and how
they line up with seven published vocabularies.

This is the conceptual model. The physical schema, with indexes, is
[`schema/dbms_research_kg.cypher`](../schema/dbms_research_kg.cypher), and the machine-checked
schema is [`schema/conformance.json`](../schema/conformance.json). Property lists and counts are in
[`schema.md`](schema.md). The allowed values of each coded property are in
[`taxonomy.md`](taxonomy.md).

It is written as prose and tables. No OWL or RDF file is published: the mappings to other
vocabularies are declared as triples inside `schema/conformance.json` and checked by
`etl.conformance.validate_ontology`.

## Scope

The graph answers one family of question: **why is a database research problem still open, and
what would it take to close it?**

So it models four things and the links between them:

| Domain | Classes |
|---|---|
| The catalog | Topic, Problem, DataSource |
| The theory | Bound, ComputationModel, Gap, Concept |
| What would close it | FutureDirection, ResearchDirection |
| Who and what | Paper, Person, Venue, Institution, Algorithm, System |

One class, TaxonomyTerm, holds the codes of the four taxonomies in [`taxonomy.md`](taxonomy.md).

Out of scope: problems the catalog does not list, citation counts from outside the catalog,
anything after the pinned commit, funding, and the real-world identity of a person.

## Properties every thing has

| Property | On | Values |
|---|---|---|
| `id` | every node | see [Identifiers](taxonomy.md#identifiers) |
| `provenance` | every node | `real` (read from the catalog), `schema-vocabulary` (a taxonomy code) |
| `source` | every node and edge | `dbms_research`, or `project_schema` for a taxonomy code |
| `method` | every node | `parsed`, `list-matched`, `keyword-classified`, `computed`, `catalog` |
| `source_url` | every node and edge | the catalog file at the pinned commit |
| `retrieved_at`, `source_date` | every node | from the source lock record, `YYYY-MM-DD` |

Every fact can be traced to a catalog page at one commit. Where a value is our rule over the page's
words rather than the words themselves, a property says which rule (`problem_type_method`,
`family_method`, `verdict_method`, `evidence_status`).

## Classes

### The catalog

| Class | Definition | Identified by |
|---|---|---|
| **Topic** | One of the 35 numbered areas of `TAXONOMY.md`. | its folder name |
| **Problem** | One open problem: one page of the catalog, with its status, statement and sections. | `<topic>/<slug>` |
| **DataSource** | The catalog itself, at the pinned commit. | `datasource:dbms_research` |

### The theory

| Class | Definition | Identified by |
|---|---|---|
| **Bound** | The best-known upper or lower bound of one problem (§4, §5), with its text and kind. | problem and direction |
| **ComputationModel** | The model a bound holds in: word-RAM, cell-probe, SETH, NP, CAP and the like. From a fixed list. | hash of the name |
| **Gap** | §6 of one problem: what separates the bounds, with a verdict. | problem |
| **Concept** | A mathematical or systems idea from a fixed list of 90, named in §2. | hash of the name |

### What would close it

| Class | Definition | Identified by |
|---|---|---|
| **ResearchDirection** | One item of §7, Current Research, of one problem. | problem and position |
| **FutureDirection** | One bullet of §8, Future Work, of one problem. | hash of problem, position and text |

### Who and what

| Class | Definition | Identified by |
|---|---|---|
| **Paper** | A work cited in §9, merged across pages when the DOI, arXiv id or title and year agree. | hash of its representative citation |
| **Person** | An author name as written in §9 or a researcher named in §7. A written name, not a verified person. | hash of the name |
| **Venue** | Where a paper appeared, normalised. | hash of the name |
| **Institution** | A university, company or lab on a checked list of 83 (82 occur), named in §7. | short name |
| **Algorithm** | A named algorithm of §3, State of the Art. | hash of the name |
| **System** | A named database system of §3. | hash of the name |
| **TaxonomyTerm** | One code of one of the four taxonomies. Schema vocabulary, not a catalog fact. | hash of scheme and code |

### Things that look alike and are not

| Pair | Difference |
|---|---|
| ResearchDirection, FutureDirection | §7 is who works on the problem now; §8 is what would close it. |
| Bound, Gap | A bound is one side; the gap is the distance between the two, as the page states it. |
| Topic, TaxonomyTerm of `dbms-topic` | The same 35 values. The Topic node is the catalog's folder; the term is its code in the topic scheme. |
| Concept, ComputationModel | A concept is what the problem rests on; a model is where a bound holds. |
| Person, a researcher | A Person node is a written name. "Wang" is many people; "T. Neumann" and "Neumann" are two nodes. |

## Relations

Read from source to target. Cardinality is per source node.

| Relation | Domain | Range | Cardinality | From |
|---|---|---|---|---|
| IN_TOPIC | Problem | Topic | 1 | the page's folder |
| CITES | Problem | Paper | 0..* | §9, with `role` and `position` |
| AUTHORED_BY | Paper | Person | 0..* | the citation, with `position` |
| APPEARED_AT | Paper | Venue | 0..1 | the citation |
| RESTS_ON | Problem | Concept | 0..* | §2 |
| GENERALIZES | Concept | Concept | 0..* | the reviewed concept hierarchy, broader to narrower |
| HAS_BOUND | Problem | Bound | 2 | §4 and §5, with `direction` |
| IN_MODEL | Bound | ComputationModel | 0..* | the bound's text |
| STATE_OF_ART | Problem | Algorithm, System | 0..* | §3, with `kind` |
| HAS_GAP | Problem | Gap | 1 | §6 |
| HAS_RESEARCH | Problem | ResearchDirection | 0..* | §7, with `position` |
| CLOSING_REQUIRES | Problem | FutureDirection | 0..* | §8, with `position` |
| ACTIVE_ON | Person, Institution | Problem | 0..* | named in §7, with the item as `direction` |
| AFFILIATED_WITH | Person | Institution | 0..* | a bracket in §7, with the text as `evidence` |
| RELATED_TO | Problem | Problem | 0..* | computed from shared papers and concepts, with `score` |
| FROM_SOURCE | Problem | DataSource | 1 | the pinned commit |
| CLASSIFIED_AS | Problem, Algorithm, System, ComputationModel | TaxonomyTerm | 1..2 | a code with `evidence_status` and `evidence` |

## Rules

| # | Rule |
|---|---|
| 1 | Every node has `id`, `provenance`, `source`, `method`, `retrieved_at`, `source_date` and `source_url`; every edge has `source` and `source_url`. |
| 2 | Every identifier is unique across the whole graph, and each relation joins one pair of nodes at most once. |
| 3 | Every edge joins the labels its relation allows, and both ends exist. |
| 4 | Every Problem has exactly one IN_TOPIC, one HAS_GAP, one FROM_SOURCE and two HAS_BOUND (upper and lower). |
| 5 | A coded property holds only a value listed in [`taxonomy.md`](taxonomy.md). |
| 6 | No value is invented. A paper with no year has no `year` property; a missing DOI, arXiv id or DBLP key is an empty string, so `x.doi <> ""` finds the papers that have one. |
| 7 | An Institution is only a name on the checked list. An AFFILIATED_WITH edge needs a §7 bracket that pairs surnames with institutions ("Suciu (UW)", "TUM (Neumann, Leis)"), never several names with several institutions, and exactly one author on the same page with that surname. |
| 8 | A GENERALIZES edge exists only for a reviewed pair, and carries its rationale. |
| 9 | A classification made by our rule says so: `evidence_status` is `rule-based`, never `verified`. |
| 10 | Nothing comes from outside the catalog: no DBLP, ORCID, citation count or later status. |

`python -m etl.local_graph verify` checks rules 1 to 5, `python -m etl.quality` and
`python -m etl.audit` check the rest.

## Alignment with other vocabularies

Seven vocabularies. Each mapping is a triple in `ontology_mapping_triples` of
`schema/conformance.json`, using `rdfs:subClassOf`, `rdfs:subPropertyOf`, `rdfs:seeAlso` or one of
our non-entailing annotations `kg:mapsTo`, `kg:mapsToScheme`, `kg:mapsToCiTO`. The project
namespace is `https://samyama.ai/kg/dbms-research/ontology#`. These describe the schema; no RDF
instance data is published.

| Vocabulary | Mapping | Limit |
|---|---|---|
| Project DBMS domain ontology | Every label, relation and property in `schema/conformance.json`, with exact domains and ranges | Defines project terms, not external facts |
| PROV-O | `source_url` locates `prov:hadPrimarySource`; `FROM_SOURCE` maps to `prov:wasDerivedFrom`; `retrieved_at` relates to `prov:generatedAtTime`; `method` names an extraction activity | A string is not asserted as a PROV entity, and retrieval time is not generation time |
| SKOS | Topic, Concept and TaxonomyTerm are `skos:Concept`; topic numbers are notation; GENERALIZES is `skos:narrower` for the reviewed pairs only | The 35 topics stay flat; no parent topic is invented |
| Dublin Core Terms | `Paper.title` → `dcterms:title`; AUTHORED_BY → `dcterms:creator`; `Paper.year` → `dcterms:issued`; IN_TOPIC → `dcterms:subject`; RELATED_TO → `dcterms:relation` | Field mapping only |
| FOAF | Person → `foaf:Person`; Institution → `foaf:Organization`; names → `foaf:name` | A catalog name does not establish identity or affiliation |
| Schema.org | Paper, Person, Institution and Venue see-also `schema:ScholarlyArticle`, `schema:Person`, `schema:Organization`, `schema:Periodical`/`schema:EventSeries` | Similarity, not subclass, where a venue's kind is unknown |
| CiTO | CITES → `cito:cites`; each `role` to its nearest CiTO property, below | Annotations, not asserted CiTO triples |

| `CITES.role` | CiTO property | Confidence |
|---|---|---|
| foundational | `cito:obtainsBackgroundFrom` | nearest meaning |
| sota | `cito:citesAsAuthority` | nearest meaning |
| survey | `cito:citesAsRecommendedReading` | nearest meaning |
| systems | `cito:citesAsDataSource` | nearest meaning; the tag is the catalog's |
| docs | `cito:citesAsSourceDocument` | nearest meaning |
| artifact | per citation; otherwise `cito:cites` | ClockBound is software and maps to `cito:cites`; CEB is a benchmark and maps to `cito:citesAsDataSource`. Both keep `role=artifact` and the raw tag |
| attack | `cito:critiques` | nearest meaning |

`kg:mapsTo` is non-entailing: an RDF exporter, if one is ever written, must apply it and keep the
difference between a literal locator and a PROV entity. CLASSIFIED_AS to `skos:related` is a
description, not an OWL entailment.

## Changing the ontology

A class or relation is declared in several places, and the tests fail until they agree:

1. `labels`, `relationships` and the property lists in `schema/conformance.json`, and its mapping
   triples if it maps to another vocabulary.
2. The index and header of `schema/dbms_research_kg.cypher`.
3. The code that builds it, in `etl/source_entities.py`, `etl/citations.py` or `etl/loader.py`.
4. `README.md`, `DATASET_CARD.md`, `docs/schema.md` and this file.
5. `docs/taxonomy.md`, if it has a coded property.
