# Taxonomies

The hierarchies in this graph, every property whose value comes from a fixed list, and the id
patterns.

The classes and relations are in [`ontology.md`](ontology.md). The external standards are in
[`standards.md`](standards.md). The lists themselves are in `codes`, `property_values` and
`taxonomy_schemes` of [`schema/conformance.json`](../schema/conformance.json), and
`etl.conformance.validate` refuses a value not on its list. A test checks every list in this file
against that spec. Counts are from the build of the pinned commit.

## Hierarchies

### Topics

Scheme `dbms-topic`, 35 terms. **Flat and source-defined**: the numbered folders of the catalog's
`TAXONOMY.md`, in its order. Every problem is in exactly one topic, read from its folder, so these
assignments are `source-explicit`. No parent grouping is invented.

`(:Problem)-[:IN_TOPIC]->(:Topic)` and `(:Problem)-[:CLASSIFIED_AS]->(:TaxonomyTerm {scheme: "dbms-topic"})`

| # | Id | Topic | Problems | Open |
|---:|---|---|---:|---:|
| 01 | `01-relational-theory` | Relational Model & Dependency Theory | 30 | 9 |
| 02 | `02-query-optimization` | Query Optimization | 31 | 15 |
| 03 | `03-query-processing` | Query Processing & Execution | 30 | 9 |
| 04 | `04-indexing-access-methods` | Indexing & Access Methods | 30 | 9 |
| 05 | `05-concurrency-control` | Concurrency Control | 30 | 12 |
| 06 | `06-recovery-logging` | Recovery, Logging & Durability | 30 | 13 |
| 07 | `07-storage-buffer` | Storage & Buffer Management | 30 | 15 |
| 08 | `08-distributed-databases` | Distributed Query Processing | 30 | 13 |
| 09 | `09-replication-consistency` | Replication & Consistency | 30 | 13 |
| 10 | `10-consensus-coordination` | Consensus & Coordination | 30 | 12 |
| 11 | `11-nosql-kv` | NoSQL & Key-Value Stores | 31 | 14 |
| 12 | `12-newsql-distributed-sql` | NewSQL & Distributed SQL | 30 | 11 |
| 13 | `13-column-stores-olap` | Column Stores & OLAP | 30 | 16 |
| 14 | `14-main-memory-db` | Main-Memory Databases | 30 | 15 |
| 15 | `15-data-integration` | Data Integration & Schema Mapping | 30 | 11 |
| 16 | `16-data-cleaning-quality` | Data Cleaning & Quality | 30 | 9 |
| 17 | `17-approximate-query-processing` | Approximate Query Processing | 30 | 13 |
| 18 | `18-streaming-queries` | Streaming & Continuous Queries | 30 | 12 |
| 19 | `19-temporal-databases` | Temporal Databases | 31 | 15 |
| 20 | `20-spatial-databases` | Spatial & Spatiotemporal Databases | 30 | 6 |
| 21 | `21-graph-databases` | Graph Databases & Graph Query Processing | 30 | 14 |
| 22 | `22-provenance-lineage` | Provenance & Lineage | 30 | 17 |
| 23 | `23-database-security` | Database Security & Access Control | 30 | 15 |
| 24 | `24-privacy-encrypted-db` | Privacy & Encrypted Databases | 30 | 17 |
| 25 | `25-query-languages-expressiveness` | Query Languages & Expressiveness | 30 | 10 |
| 26 | `26-cardinality-estimation` | Cardinality Estimation & Statistics | 30 | 16 |
| 27 | `27-learned-db-components` | Learned Database Components | 30 | 19 |
| 28 | `28-vector-similarity-search` | Vector Databases & Similarity Search | 30 | 10 |
| 29 | `29-hardware-conscious-db` | Hardware-Conscious Databases | 30 | 8 |
| 30 | `30-cloud-serverless-db` | Cloud & Serverless Databases | 30 | 13 |
| 31 | `31-time-series-db` | Time-Series Databases | 30 | 12 |
| 32 | `32-multimodel-document-db` | Multi-Model & Document Databases | 30 | 14 |
| 33 | `33-benchmarking-testing` | Benchmarking, Testing & Verification | 30 | 10 |
| 34 | `34-schema-design-normalization` | Schema Design & Normalization | 30 | 11 |
| 35 | `35-autonomous-db` | Self-Driving / Autonomous Databases | 30 | 22 |

### Concepts

90 concepts from a fixed list (`CONCEPTS` in `etl/source_entities.py`), matched in §2 of each page.
A reviewed hierarchy of **31 broader-narrower pairs** (`CONCEPT_HIERARCHY`), each edge with
`method = curated-hierarchy` and a one-sentence `rationale` naming the textbook relation. A pair is
emitted only when both concepts occur in the graph.

`(:Concept)-[:GENERALIZES]->(:Concept)`, broader to narrower, `skos:narrower`.

| Broader | Narrower |
|---|---|
| submodular width | fractional hypertree width |
| fractional hypertree width | hypertree width |
| hypertree width | treewidth |
| hypertree width | acyclicity |
| acyclicity | join tree |
| union of conjunctive queries | conjunctive query |
| Datalog | union of conjunctive queries |
| first-order logic | conjunctive query |
| join dependency | multivalued dependency |
| multivalued dependency | functional dependency |
| tuple-generating dependency | join dependency |
| semiring | provenance semiring |
| data provenance | provenance semiring |
| consensus | Paxos |
| consensus | Raft |
| consensus | Byzantine fault tolerance |
| consistency model | linearizability |
| consistency model | causal consistency |
| consistency model | eventual consistency |
| consistency model | serializability |
| consistency model | snapshot isolation |
| sketch (streaming) | HyperLogLog |
| sketch (streaming) | Count-Min sketch |
| sketch (streaming) | Bloom filter |
| sampling | reservoir sampling |
| nearest neighbor search | HNSW |
| nearest neighbor search | locality-sensitive hashing |
| nearest neighbor search | product quantization |
| submodularity | polymatroid |
| entropy | Shearer's lemma |
| fractional edge cover | AGM bound |

### Project schemes

Three flat schemes of our own. No source taxonomy defines them, so every assignment is
`rule-based` and its `evidence` says which rule fired. They need a reviewer's approval before a
production load.

**Problem type** (scheme `problem-type`, 11 terms), on `Problem.problem_type`.
The first keyword rule that matches the title and §1 decides (`problem_type_method = statement-rule`);
when none does, the page's topic decides through the `TOPIC_PROBLEM_TYPE` crosswalk in
`etl/source_entities.py` (`topic-crosswalk`).

| Code | Records | Meaning |
|---|---:|---|
| `query-evaluation` | 133 | Evaluating a query: joins, operators, complexity of evaluation |
| `query-optimization` | 159 | Choosing a plan: cost models, cardinality, plan search |
| `data-modeling` | 97 | Data models, dependencies, normal forms, query languages |
| `data-integration` | 38 | Integration, schema mapping, cleaning |
| `transaction-processing` | 162 | Concurrency, recovery, isolation |
| `storage-indexing` | 170 | Storage layouts, buffers, indexes |
| `distributed-data` | 128 | Distribution, replication, consensus |
| `analytics` | 85 | OLAP, approximate and streaming analytics |
| `system-design` | 81 | Architecture, hardware, cloud, autonomy |
| `other` | 0 | Allowed; no problem falls here |
| `unclassified` | 0 | Allowed; every problem gets a type |

**Solution or technique family** (scheme `solution-technique-family`, 14 terms), on
`Algorithm.family` and `System.family`. A rule over the name decides (`family_method = name-rule`);
otherwise the majority topic of the pages citing the name decides through `TOPIC_TECHNIQUE_FAMILY`
(`topic-crosswalk`). Counts are algorithms and systems together.

| Code | Records | Meaning |
|---|---:|---|
| `join-processing` | 28 | Join algorithms |
| `query-optimization` | 90 | Optimisers and plan search |
| `decomposition` | 93 | Decompositions and widths |
| `indexing` | 192 | Indexes and access methods |
| `transaction-processing` | 102 | Concurrency control and recovery |
| `distributed-processing` | 189 | Distributed and replicated processing |
| `analytics` | 184 | Analytics and approximation |
| `storage` | 201 | Storage engines and layouts |
| `relational-dbms` | 35 | A relational DBMS |
| `analytical-dbms` | 25 | An analytical DBMS |
| `streaming-system` | 33 | A streaming system |
| `query-engine` | 186 | A query engine |
| `other` | 209 | A named method no rule or crosswalk places |
| `unclassified` | 0 | Allowed; every name gets a family |

**Computational model or workload** (scheme `computation-model-workload`, 17 terms), on
`ComputationModel.class`. A model needs an explicit phrase in §4 or §5 (`MODELS` in
`etl/source_entities.py`). Counts are models, not bounds.

| Code | Records | Meaning |
|---|---:|---|
| `word-ram` | 1 | Word-RAM |
| `cell-probe` | 1 | Cell-probe |
| `external-memory` | 2 | External memory, I/O model |
| `comparison` | 1 | Comparison model |
| `streaming` | 1 | Streaming |
| `parallel` | 2 | Parallel, MPC, PRAM |
| `turing` | 0 | Turing machine |
| `fine-grained` | 1 | Fine-grained hypotheses: SETH, 3SUM, APSP, OMv |
| `complexity-class` | 1 | NP, coNP, PSPACE, W[1], undecidability |
| `information-theoretic` | 1 | Information-theoretic |
| `distributed-impossibility` | 1 | CAP, FLP, PACELC |
| `online` | 1 | Online, competitive analysis |
| `communication` | 1 | Communication complexity |
| `cryptographic` | 1 | Cryptographic assumptions |
| `statistical` | 1 | Statistical |
| `other` | 0 | Allowed; no model falls here |
| `unclassified` | 0 | Allowed; every model is classified |

Codes no record uses yet stay in the scheme as TaxonomyTerm nodes with no edge: `other` (computation-model-workload), `other` (problem-type), `turing` (computation-model-workload), `unclassified` (computation-model-workload), `unclassified` (problem-type), `unclassified` (solution-technique-family).

## Controlled vocabularies

The twelve code lists of `codes` in `schema/conformance.json`.

### Problem.status

As written in the page header.

| Value | Count | Meaning |
|---|---:|---|
| `open` | 450 | No algorithm or bound settles it |
| `partially-solved` | 369 | Settled for some cases or models, open for others |
| `empirically-open` | 227 | The theory is known; what works in practice is not |
| `solved-but-impractical` | 7 | Settled in theory, with no practical method |
| `stale` | 0 | Allowed by the catalog's template; no page uses it |

### CITES.role

The bold tag of the reference in §9. The original text is kept in `role_raw`.

| Value | Count | Meaning |
|---|---:|---|
| `foundational` | 2,777 | `[Foundational]`: the result the problem rests on |
| `sota` | 2,633 | `[SOTA]`: the current best result |
| `survey` | 676 | `[Survey]` |
| `systems` | 11 | `[Systems]` |
| `docs` | 5 | `[Docs]`: vendor or project documentation |
| `artifact` | 2 | `[Artifact]`: software or a benchmark |
| `attack` | 2 | `[Attack]`: a result that breaks a scheme |
| `mixed` | 12 | Several recognised tags on one reference |
| `unclassified` | 39 | No tag, or a tag that is not a role, such as `[Lower Bound]`; the text stays in `role_raw` |

### Gap.verdict

The page's own bold verdict wins. Otherwise a keyword rule over §6; a closed phrase together with an
open, partial or empirical phrase gives `partially-solved`. `verdict_method` says which decided.

| Value | Count | Meaning |
|---|---:|---|
| `open` | 412 | The bounds do not meet |
| `partially-solved` | 477 | They meet for part of the problem |
| `empirically-open` | 90 | The open part is about practice, not theory |
| `closed` | 20 | The bounds meet |
| `unstated` | 54 | Neither the page nor the keyword rule gives a verdict |

### Bound.kind

Rules in `etl/classify.py`. A lower bound with hardness or impossibility wording is
`impossibility`; otherwise complexity notation or time words give `time`, space words `space` (the
more frequent wins when both occur).

| Value | Count | Meaning |
|---|---:|---|
| `time` | 1,102 | Running time, or complexity notation |
| `space` | 47 | Space or memory |
| `impossibility` | 931 | A lower bound by hardness or impossibility |
| `approximation` | 15 | An approximation ratio or error guarantee |
| `unclassified` | 11 | None of the above applies |

### STATE_OF_ART.kind

| Value | Count | Meaning |
|---|---:|---|
| `theory` | 854 | An algorithm |
| `systems` | 3,204 | A system |

### Person.name_form

The shape of the name as written. Names are never merged across forms.

| Value | Count | Meaning |
|---|---:|---|
| `full` | 1,060 | Given name and surname, `Thomas Neumann` |
| `initials` | 1,601 | Initials and surname, `T. Neumann` |
| `surname` | 1,793 | Surname only, `Neumann` |

### Venue.kind

| Value | Count | Meaning |
|---|---:|---|
| `conference` | 215 | SIGMOD, VLDB, PODS, ICDE and the like |
| `journal` | 219 | TODS, VLDB Journal, JACM and the like |
| `preprint` | 24 | arXiv and similar |
| `book` | 30 | A book or book chapter |
| `report` | 39 | A technical report, thesis or vendor document |
| `other` | 150 | Anything else; some are fragments of the citation, kept as written |

### Institution.kind

| Value | Count | Meaning |
|---|---:|---|
| `academic` | 63 | A university or its lab |
| `industry` | 18 | A company or its lab |
| `government` | 1 | A government lab |
| `non-profit` | 0 | Allowed; no institution on the list uses it yet |

### Problem.problem_type, Algorithm.family, System.family, ComputationModel.class

The project schemes above.

### CLASSIFIED_AS.evidence_status

| Value | Count | Meaning |
|---|---:|---|
| `source-explicit` | 1,053 | The page states it: the topic, from the page's folder |
| `rule-based` | 2,636 | One of our rules decided it, and `evidence` says which |
| `unresolved` | 0 | Allowed; no assignment is unresolved |

## How a value was decided

Not code lists of the catalog's, but closed lists all the same: each says which step or rule set a
value, so a reader can tell the page's words from ours.

### Gap.verdict_method

| Value | Count | Meaning |
|---|---:|---|
| `stated` | 139 | The bold phrase that opens §6 |
| `keyword` | 860 | A keyword rule over the whole of §6 |
| `none` | 54 | Neither gives a verdict |

### Problem.problem_type_method

| Value | Count | Meaning |
|---|---:|---|
| `statement-rule` | 781 | A keyword rule over the title and §1 |
| `topic-crosswalk` | 272 | No rule fired; the page's topic decides |
| `none` | 0 | Allowed; never needed |

### Algorithm.family_method

| Value | Count | Meaning |
|---|---:|---|
| `name-rule` | 139 | A rule over the name |
| `topic-crosswalk` | 446 | No rule fired; the majority topic of the citing pages decides |
| `none` | 0 | Allowed; never needed |

### System.family_method

| Value | Count | Meaning |
|---|---:|---|
| `name-rule` | 217 | A rule over the name |
| `topic-crosswalk` | 765 | No rule fired; the majority topic of the citing pages decides |
| `none` | 0 | Allowed; never needed |

### Paper.parse_status

| Value | Count | Meaning |
|---|---:|---|
| `parsed` | 2,345 | Title, and year where present, read from the citation |
| `uncertain` | 334 | The citation could not be split; only `citation_text` is kept, and no title is invented |

### CITES.verification_status

| Value | Count | Meaning |
|---|---:|---|
| `source_only` | 6,142 | As the catalog cites it; not checked against any outside record |
| `unverified` | 15 | The reference's own text says it is unverified |

### CITES.role_status

| Value | Count | Meaning |
|---|---:|---|
| `source-explicit` | 6,118 | The role is the page's tag |
| `unresolved` | 39 | No role tag |

## Identifiers

Ids are deterministic: the same pinned commit gives the same ids. Problem and Topic keep the
catalog's own path; other ids hash a normalised key with SHA-256 and keep 24 hex characters.

| Class | Pattern | Example | Value is |
|---|---|---|---|
| Topic | `<nn>-<slug>` | `01-relational-theory` | the catalog folder |
| Problem | `<topic>/<slug>` | `01-relational-theory/acyclic-join-dependencies` | the page path |
| Gap | `<problem>#gap` | `01-relational-theory/acyclic-join-dependencies#gap` | one per problem |
| ResearchDirection | `<problem>#research-<n>` | `…/acyclic-join-dependencies#research-1` | position in §7 |
| Bound | `bound:<problem>:<upper\|lower>` | `bound:01-relational-theory/acyclic-join-dependencies:upper` | problem and direction |
| FutureDirection | `future:<hash>` | `future:a490732899e9cf8a216b3a66` | problem, position and text |
| Paper | `paper:<hash>` | `paper:abda98318c49f98b20a0adf5` | the representative citation of the merged work |
| Person | `person:<hash>` | `person:e29a7f31cac05abc97e12380` | the written name |
| Venue | `venue:<hash>` | `venue:62d7eacf08f2331224f18770` | the normalised name |
| Concept | `concept:<hash>` | `concept:d841fe1cf43c2678896f6977` | the list name |
| Algorithm | `algorithm:<hash>` | `algorithm:94b0347165108ddd1d5853f8` | the normalised name |
| System | `system:<hash>` | `system:f3ebc350c88c05e1d9d04583` | the normalised name |
| ComputationModel | `model:<hash>` | `model:f926599c5d3fa47c4b87d53e` | the list name |
| Institution | `institution:<key>` | `institution:mit` | the list key |
| TaxonomyTerm | `taxonomy:<hash>` | `taxonomy:4e912efbb3dde79dd5722d44` | scheme and code |
| DataSource | `datasource:dbms_research` | | the catalog |

Changing a citation's wording or order can change which citation represents a merged Paper, and so
its id. That is a limit of building ids from the source; it is not bibliographic identity.
