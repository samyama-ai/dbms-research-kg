# DBMS Research KG — Knowledge Resource Inventory

**Status:** v1 implementation decision  
**Scope:** Build-time inventory for `dbms-research-kg`; no proposed or future-only items are counted.  
**Source-data rule:** Graph instance data must come only from the pinned `dbms_research` catalog at commit `5fff7f74508a52ac238f3bb608b8c8c872489fec` (2026-09-09). Do not fetch or import external records, paper metadata, author profiles, taxonomy members, or ontology instances. External resources below are schema-level models/specifications to follow or map to; reference their names and official documentation rather than copying their term datasets into the graph. The catalog is documented as CC BY 4.0 in `schema.md`; retain source attribution and provenance.

## 1. Final v1 inventory targets

These are the counts to implement in v1. They are not claims that the graph has already been built; confirm the counts after the build and validation pass.

| Category | Final v1 count | Breakdown | Build-time interpretation |
|---|---:|---|---|
| Ontologies / ontology vocabularies | **7** | 1 project-defined domain model + 6 external vocabularies followed at schema/mapping level | Define the DBMS Research KG model and document mappings to established vocabularies. Do not import external instances or ontology datasets. |
| Taxonomies | **4** | 1 existing source taxonomy + 3 project-defined taxonomies derived only from catalog pages | Implement the 35-topic taxonomy plus three reviewed hierarchical classifications built from the catalog's own content. |
| Coding systems / controlled code lists | **12** | 0 external coding systems imported + 12 project-defined code lists | Retain the 8 existing schema code lists and add 4 code lists. Do not count DOI/arXiv/DBLP identifiers as coding systems. Parse identifiers only when they are present in source text. |
| Standards / specifications followed | **6** | 6 followed in v1; 0 proposed-only; 0 future-only | Apply the relevant metadata, provenance, taxonomy, date, query-language, and license-expression conventions now. This count is of standards/specifications, not external datasets. |

**Counting rule:** A resource may be relevant to more than one category (for example, SKOS is a vocabulary and a W3C Recommendation). Counts are per inventory category and must not be summed into a grand total. Do not report a planned item as implemented until its mapping/rule is represented in code or schema and tested.

## 2. Ontologies / vocabularies — 7

| # | Resource | Role in this KG | Implementation boundary |
|---:|---|---|---|
| 1 | DBMS Research KG domain model (own) | Problems, topics, papers, people, venues, institutions, concepts, algorithms, systems, bounds, computation models, gaps, research directions, future directions, and data source | Implement as the project's labelled property graph schema in `schema.md`; this is the KG's own domain model, not a separately published OWL ontology. |
| 2 | W3C PROV-O | Provenance and derivation concepts | Map existing provenance fields (`source`, `source_url`, `retrieved_at`, `source_date`, `method`, `enriched_by`) in documentation; do not import PROV-O data. https://www.w3.org/TR/prov-o/ |
| 3 | W3C SKOS | Concept schemes and broader/narrower taxonomy relations | Use as a mapping pattern for taxonomy hierarchy and concept labels; retain graph-native edges/properties. https://www.w3.org/TR/skos-reference/ |
| 4 | Dublin Core Metadata Terms | Descriptive metadata for papers and source records | Map applicable metadata concepts such as title, creator, identifier, source, and date; do not copy external metadata records. https://www.dublincore.org/specifications/dublin-core/dcmi-terms/ |
| 5 | FOAF | Person and organization description vocabulary | Use only as a schema-mapping reference for person/organization concepts; no external profiles imported. http://xmlns.com/foaf/spec/ |
| 6 | Schema.org | Scholarly article, person, and organization concepts | Use only as a mapping reference; no Schema.org records or external article data imported. https://schema.org/ |
| 7 | CiTO (Citation Typing Ontology) | Semantics of citation relationships | Map only citation roles that can be supported by catalog evidence; do not infer citation semantics not stated by the source. https://sparontologies.github.io/cito/current/cito.html |

**Important terminology:** item 1 is the project-defined graph domain model. Items 2–7 are external vocabularies/ontology references followed at the model level, not external data sources for graph instances. Avoid claiming the project has implemented OWL reasoning or loaded these vocabularies as graph nodes.

## 3. Taxonomies — 4

All taxonomy membership and labels must be derived from the pinned catalog. No ACM CCS, arXiv, or other external taxonomy members are imported in v1.

| # | Taxonomy | Source and construction | Implementation requirement |
|---:|---|---|---|
| 1 | Existing DBMS topic taxonomy | `TAXONOMY.md`, 35 topics | Preserve the 35 source topics and stable topic IDs. Add the planned `scope` property from the source taxonomy where present. |
| 2 | Problem-type taxonomy | Problem titles, statements, and topic assignments from catalog pages | Create a reviewed hierarchy of DBMS problem families. Each assignment must cite the originating problem page and use a documented classification rule. |
| 3 | Technique/solution-family taxonomy | Catalog §2 concepts and §3 state-of-the-art algorithms/systems | Create a hierarchy for solution families represented in the catalog. Do not add techniques merely because they are common in the wider field. |
| 4 | Computational-model taxonomy | Catalog §4/§5 bound text and computation-model mentions | Create a hierarchy only for model classes evidenced in the catalog; preserve raw text when classification is uncertain. |

For taxonomies 2–4, use stable project-owned IDs, include `source_url`/provenance back to the source problem, and mark uncertain assignments as unresolved rather than inventing certainty. Review the resulting hierarchy before freezing the v1 schema. These are project-derived taxonomies, not externally standardized classifications.

## 4. Coding systems / controlled code lists — 12

The existing schema lists eight controlled code lists. Keep those eight and implement the four additions below. These are project-defined value sets, not external code systems.

| # | Code list | Allowed values / definition source | Status for v1 |
|---:|---|---|---|
| 1 | `Problem.status` | `open`, `partially-solved`, `empirically-open`, `solved-but-impractical`; allow `stale` only if encountered in source, otherwise document it as template-allowed but unused | Existing; preserve source values |
| 2 | `CITES.role` | `foundational`, `sota`, `survey`, `systems`, `docs`, `artifact`, `attack` | Existing; parse the catalog's tags |
| 3 | `Gap.verdict` | `open`, `partially-solved`, `empirically-open`, `closed`, `unstated` | Existing plan; retain `verdict_method` and raw text to distinguish stated from rule-classified values |
| 4 | `Bound.kind` | `time`, `space`, `impossibility` | Existing |
| 5 | `STATE_OF_ART.kind` | `theory`, `systems` | Existing |
| 6 | `Person.name_form` | `full`, `initials`, `surname` | Existing |
| 7 | `Venue.kind` | `conference`, `journal`, `preprint`, `other` | Existing; derive only from available catalog evidence |
| 8 | `Institution.kind` | `academic`, `industry`, `government`, `non-profit` | Existing; use the project's checked list and source evidence only |
| 9 | `Problem.type` | Project-owned hierarchy from the problem-type taxonomy | Add and validate in v1 |
| 10 | `Technique.family` | Project-owned hierarchy from the technique/solution-family taxonomy | Add and validate in v1 |
| 11 | `ComputationModel.class` | Project-owned hierarchy from model mentions in §4/§5 | Add and validate in v1 |
| 12 | `Evidence.status` | `explicit-in-source`, `rule-classified`, `unresolved` | Add to distinguish source statements from parser/classifier outputs |

**External identifier handling:** DOI, arXiv IDs, DBLP keys, ORCID IDs, ROR IDs, ISSN, and ISBN are identifiers, not project code lists. Do not count them as external coding systems. Extract/store an identifier only if it is already present in the catalog page; do not enrich from external APIs. An absent identifier remains absent.

## 5. Standards / specifications followed — 6

These are design and implementation references. This inventory does not authorize importing external records or copying full standards text.

| # | Standard/specification | How v1 follows it | Official reference |
|---:|---|---|---|
| 1 | W3C PROV-O / PROV data model | Keep source, retrieval time, source date, derivation method, and enrichment provenance explicit; document their correspondence to provenance concepts | https://www.w3.org/TR/prov-o/ |
| 2 | W3C SKOS | Represent taxonomy labels and hierarchy with explicit, documented broader/narrower semantics | https://www.w3.org/TR/skos-reference/ |
| 3 | Dublin Core Metadata Terms / ISO 15836 family | Use compatible meanings for title, creator, identifier, source, and date metadata where applicable; do not claim full conformance without a formal application profile | https://www.dublincore.org/specifications/dublin-core/dcmi-terms/ and https://www.iso.org/standard/71339.html |
| 4 | ISO 8601 date/time conventions | Store dates in a consistent machine-readable form; retain the source's year/month granularity when the source does not give a full date | https://www.iso.org/iso-8601-date-and-time-format.html |
| 5 | openCypher | Use the graph engine's supported openCypher query language for graph access and validation queries | https://opencypher.org/ |
| 6 | SPDX license-expression conventions | Record the source catalog's declared license as metadata and preserve attribution; do not use SPDX as a reason to import third-party content | https://spdx.org/specifications/ |

The wording “follows” means the project applies the relevant conventions described in this table. It does not claim formal certification or complete conformance to every clause of each specification.

## 6. Source-data and licensing boundary

1. The only source of graph instance data is the pinned `dbms_research` catalog. The build must not call DBLP, Crossref, OpenAlex, ORCID, ROR, arXiv APIs, or other external APIs to enrich records.
2. External vocabularies/specifications are referenced for modeling guidance only. Do not bulk-download their vocabularies, taxonomies, or instance data into the graph for v1.
3. Do not import ACM CCS or arXiv subject-classification records as taxonomy membership data. The additional taxonomies in §3 are constructed only from the DBMS catalog.
4. Preserve catalog attribution, pinned commit, retrieval timestamp, source page URL, and the license metadata supplied by the catalog. The existing `schema.md` records the source as CC BY 4.0; verify the pinned source's license file before release and include required attribution.
5. If an identifier or classification cannot be found in the source catalog, leave it missing. No inferred external facts should be written as source facts.

## 7. Build acceptance checklist

- [ ] `docs/schema.md` links to this inventory and describes the four taxonomy schemes and twelve code lists.
- [ ] `docs/standards.md` is committed with this inventory.
- [ ] Parser reads only the pinned local catalog and has no external enrichment calls.
- [ ] The three new taxonomies have stable IDs, documented classification rules, source-page provenance, and an explicit unresolved state.
- [ ] Every own code list has a central definition and validation tests; invalid values are rejected or preserved as unresolved, not silently coerced.
- [ ] Ontology/vocabulary mappings are documented; external vocabulary instances are not imported.
- [ ] Build output reports actual graph node/edge/label/type counts separately from the resource inventory counts.
- [ ] A post-build audit verifies that every claimed ontology mapping, taxonomy, code list, and standard is represented in documentation/code and has tests or a concrete schema mapping.

## References

- DBMS Research source catalog pinned in `docs/schema.md`: `https://github.com/samyama-ai/dbms_research`, commit `5fff7f74508a52ac238f3bb608b8c8c872489fec`.
- W3C PROV-O: https://www.w3.org/TR/prov-o/
- W3C SKOS: https://www.w3.org/TR/skos-reference/
- Dublin Core Metadata Terms: https://www.dublincore.org/specifications/dublin-core/dcmi-terms/
- ISO 15836-1:2017: https://www.iso.org/standard/71339.html
- FOAF: http://xmlns.com/foaf/spec/
- Schema.org: https://schema.org/
- CiTO: https://sparontologies.github.io/cito/current/cito.html
- ISO 8601: https://www.iso.org/iso-8601-date-and-time-format.html
- openCypher: https://opencypher.org/
- SPDX specifications: https://spdx.org/specifications/
