---
license: cc-by-4.0
pretty_name: DBMS Research Knowledge Graph
tags:
  - knowledge-graph
  - samyama
  - property-graph
  - database-systems
  - open-problems
  - research
language:
  - en
size_categories:
  - 10K<n<100K
---

# Dataset Card for `dbms-research-kg`

**20,211 nodes. 53,721 edges. The 1,053 open problems of database systems research, with the
papers, people, institutions, algorithms, systems, bounds and gaps behind them, from one pinned
source.**

> Part of the **Samyama** ecosystem. This card describes the dataset; the repository holds the
> loader and source-data specifics.

## Summary

A property graph of open problems in database systems research: for each problem, its topic and
status, the best-known upper and lower bounds and the model each holds in, the gap between them, the
papers it rests on, who is working on it, and the future work that would close it.

| Layer | Nodes | What it holds |
|---|---:|---|
| The catalog | 35 topics, 1,053 problems | the taxonomy and one page per open problem, with its status |
| The theory | 2,106 bounds, 16 computation models, 1,053 gaps, 90 concepts | upper and lower bounds and the model each holds in, the gap with its verdict, the ideas a problem rests on |
| What would close it | 3,825 future-work items, 2,496 current-research items | the page's Future Work and Current Research, item by item |
| Who and what | 2,679 papers, 4,454 author names, 677 venues, 82 institutions, 982 systems, 585 algorithms | the evidence each page cites, the groups it names, the state of the art |

Everything is read from the catalog. Where a value is our rule over the page's words (a problem
type, a technique family, a gap verdict), the graph records which rule. Every node and edge carries
`source_url`, the catalog file at the pinned commit.

## Intended use

- Exploring a research area: what is open, why, who works on it, what it rests on.
- Finding research opportunities: open gaps, problems with little recent work, shared future work.
- Demonstrating graph queries, graph algorithms and agents over a scholarly graph.
- Teaching and testing: loaders, query engines, MCP tools.

## Not suitable for

- **Statements about real people.** A Person is a name as written; "Wang" is many people. No
  identity is resolved and no affiliation is verified.
- **Citation metrics.** A paper's count is the number of catalog pages that cite it, not its
  citations in the field.
- **The current state of a problem.** The catalog is a snapshot of 2026-09-09.
- **A primary source.** The catalog describes itself as a synthesized study aid. Cite the papers,
  not the graph.

## Structure

**16 node labels** -- Problem, Topic, Paper, Person, Venue, Institution, Concept, Algorithm, System,
Bound, ComputationModel, Gap, ResearchDirection, FutureDirection, DataSource, TaxonomyTerm

**17 edge types** -- IN_TOPIC, CITES, AUTHORED_BY, APPEARED_AT, RESTS_ON, GENERALIZES, HAS_BOUND,
IN_MODEL, STATE_OF_ART, HAS_GAP, HAS_RESEARCH, CLOSING_REQUIRES, ACTIVE_ON, AFFILIATED_WITH,
RELATED_TO, FROM_SOURCE, CLASSIFIED_AS

| Label | Count |
|---|---:|
| Person | 4,454 |
| FutureDirection | 3,825 |
| Paper | 2,679 |
| ResearchDirection | 2,496 |
| Bound | 2,106 |
| Problem | 1,053 |
| Gap | 1,053 |
| System | 982 |
| Venue | 677 |
| Algorithm | 585 |
| Concept | 90 |
| Institution | 82 |
| TaxonomyTerm | 77 |
| Topic | 35 |
| ComputationModel | 16 |
| DataSource | 1 |

Every property and edge count is in [`docs/schema.md`](docs/schema.md).

## Provenance and licence

| Source | Supplies | Terms |
|---|---|---|
| [DBMS Research catalog](https://github.com/samyama-ai/dbms_research) at commit `5fff7f74508a52ac238f3bb608b8c8c872489fec` | everything | CC BY 4.0 |

The graph's content falls under the catalog's CC BY 4.0, so the frontmatter is `cc-by-4.0`. Credit:

> Source: DBMS Research catalog, samyama-ai/dbms_research, CC BY 4.0.

The repository's code is Apache 2.0. That licence does not cover the data.

This is a reading of the stated licence, made on 2026-10-14. It is not legal advice.

## How the graph is made

- **Parsed** from each page's header and its ten sections, by `etl/source_parser.py` and
  `etl/loader.py`.
- **Matched** against fixed lists we keep in code: 90 concepts, 83 institutions, the computation
  models, and the names of algorithms and systems in §3.
- **Classified** by our rules into four taxonomies (topic, problem type, technique family, model
  class); each assignment records its evidence and is marked `rule-based`, except the topic, which
  is the page's own.
- **Computed**: RELATED_TO links problems that share papers or concepts, with a Jaccard score.

No language model extracts anything, and nothing is looked up outside the catalog.

## Personal and sensitive data

The graph holds author and researcher **names as the catalog writes them**, the papers they wrote,
and the institutions named next to them. No contact details, identifiers or other personal data.
An affiliation is what a page states, not a verified fact.

## Reproducing

```bash
pip install -e ".[dev]"
python -m etl.download_data          # the catalog at the pinned commit
python -m etl.source_parser          # pages -> build/source_catalog.json
python -m etl.local_graph build-catalog-candidate --catalog build/source_catalog.json \
  --output build/dbms_research_kg.schema-candidate-v6.sqlite
python -m etl.loader --catalog build/source_catalog.json --url http://127.0.0.1:8094 --load
```

A snapshot (`.sgsnap` with its manifest) is shared within the team, outside git. No downloaded
data is committed to the repository.

## Known limitations

- **Names are not merged.** "T. Neumann", "Thomas Neumann" and "Neumann" are three nodes; 1,793
  names are a surname only.
- **334 citations do not parse**; their text is kept and no title is made up. 364 papers have no
  year.
- **Venue names are as written**; 150 of 677 are kind `other`, some of them fragments of a citation.
- **Our taxonomies are unreviewed.** Problem type, technique family and model class are rules of
  this project, not the catalog's, and await a domain reviewer.
- **The catalog's pages are synthesized**, not expert-verified, and the graph is only as right as
  they are.
- **No vectors.** Similar problems by meaning need embeddings, which this build does not compute.

Full detail is in [`docs/data-provenance.md`](docs/data-provenance.md).

## Verification

- `python -m etl.local_graph verify`: schema, unique ids, edge ends, provenance, and the seven
  vocabulary alignments.
- `python -m etl.quality`: 18 content criteria, all passing ([report](benchmarks/quality-report.md)).
- `python -m etl.audit`: 4 taxonomies, 12 code lists and 6 standards, item by item, all passing
  ([report](benchmarks/audit-report.md)).
- The 48 scope questions: each answer is recomputed from the raw pages without the graph parser,
  with 0 wrong ([benchmark](benchmarks/scope_questions.md)).
- The loader counts every label and edge type on the engine against its plan, and fails on any
  difference. The counts on this card are checked against the build by the test suite.

## Links

| | |
|---|---|
| Source catalog | [github.com/samyama-ai/dbms_research](https://github.com/samyama-ai/dbms_research) |
| Samyama Graph | [github.com/samyama-ai/samyama-graph](https://github.com/samyama-ai/samyama-graph) |
| The Book | [samyama-ai.github.io/samyama-graph-book](https://samyama-ai.github.io/samyama-graph-book/) |
| Contact | [samyama.dev/contact](https://samyama.dev/contact) |
