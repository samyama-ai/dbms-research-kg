# DBMS Research Knowledge Graph

**20,211 nodes. 53,721 edges. The 1,053 open problems of database systems research, with the
papers, people, institutions, algorithms, systems, bounds and gaps behind them, from one pinned
source.**

> Part of the **Samyama** ecosystem — loaded into and queried via the graph engine at [samyama-ai/samyama-graph](https://github.com/samyama-ai/samyama-graph).
> This repo holds the loader and source-data specifics for the KG.

![DBMS Research KG demo](demo/dbms-research-kg.gif)

<a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="License"></a>

---

## What is in it

| Layer | Nodes | What it holds |
|---|---:|---|
| **The catalog** | 1,089 | 35 topics, 1,053 problem pages with their status, and the catalog itself |
| **The theory** | 3,265 | upper and lower bounds, the model each holds in, the gap between them, 90 concepts |
| **What would close it** | 6,321 | each page's Current Research and Future Work, item by item |
| **Who and what** | 9,459 | cited papers, author names, venues, institutions, named algorithms and systems |
| **Taxonomy codes** | 77 | the codes of four taxonomies, as SKOS concepts |

**Everything is read from one source**, the
[DBMS Research catalog](https://github.com/samyama-ai/dbms_research) at commit `5fff7f7`. Nothing is
looked up elsewhere, nothing is generated, and no language model extracts anything.

**Some values are our rules, and say so.** Problem types, technique families, model classes, gap
verdicts, the concept hierarchy and the institution list are this project's rules over the page's
words. Each records the rule that set it, and every node and edge carries `source_url`, the catalog
file at the pinned commit.

## Terms of use

The catalog is CC BY 4.0, so the graph may be used for any purpose, including commercial use and
public display, with credit:

> Source: DBMS Research catalog, samyama-ai/dbms_research, CC BY 4.0.

The catalog calls itself a synthesized study aid, not a primary source: cite the papers, not the
graph. Details are in [`docs/data-provenance.md`](docs/data-provenance.md).

---

## A question about the field

> *"Which papers are cited by the most open problems?"*

```cypher
MATCH (p:Problem)-[:CITES]->(paper:Paper)
WITH paper, count(p) AS problems
RETURN paper.title AS paper, paper.year AS year, problems
ORDER BY problems DESC, paper LIMIT 5
```

| Paper | Year | Problems |
|---|---:|---:|
| Foundations of Databases | 1995 | 65 |
| Size Bounds and Query Plans for Relational Joins | 2008 | 56 |
| Access Path Selection in a Relational Database Management System | 1979 | 48 |
| The Input/Output Complexity of Sorting and Related Problems | 1988 | 39 |
| Spanner: Google's Globally-Distributed Database | 2012 | 37 |

The count is of catalog pages that cite the paper, not of its citations in the field.

## A question about one problem

> *"When should a database use a worst-case-optimal join instead of a tree of binary joins: why is
> that still open?"*

```cypher
MATCH (p:Problem {id: "03-query-processing/hybrid-binary-wcoj-optimization"})-[:HAS_GAP]->(g:Gap)
MATCH (p)-[:HAS_BOUND]->(b:Bound)
OPTIONAL MATCH (b)-[:IN_MODEL]->(m:ComputationModel)
RETURN p.status AS status, g.verdict AS gap, b.direction AS bound, b.kind AS kind,
       collect(m.name) AS models
ORDER BY bound DESC
```

| Status | Gap | Bound | Kind | Models |
|---|---|---|---|---|
| open | open | upper | time | word-RAM |
| open | open | lower | impossibility | SETH / fine-grained, NP / classical |

The upper bound is an algorithm's running time; the lower bound holds only under SETH or NP
hardness, and nothing bridges the two. The gap's verdict is the page's own words, read by a rule.

---

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

python -m etl.download_data          # the catalog at the pinned commit -> data/ (+ lock file)
python -m etl.source_parser          # pages -> build/source_catalog.json
python -m etl.local_graph build-catalog-candidate \
  --catalog build/source_catalog.json \
  --output build/dbms_research_kg.schema-candidate-v6.sqlite
pytest                               # parts that need the catalog or a build skip without them
```

The build needs no engine and takes about 15 seconds. Then check it:

```bash
G=build/dbms_research_kg.schema-candidate-v6.sqlite
python -m etl.local_graph verify --graph $G    # schema, ids, endpoints, provenance, 7 alignments
python -m etl.quality --graph $G               # 18 content criteria
python -m etl.audit --graph $G                 # 4 taxonomies, 12 code lists, 6 standards
python -m benchmarks.reference                 # the 48 scope questions, checked against the raw pages
```

### Load into a running Samyama server

```bash
docker run -d --name samyama-dbms -p 127.0.0.1:8094:8080 ghcr.io/samyama-ai/samyama-graph:latest
python -m etl.loader --catalog build/source_catalog.json --url http://127.0.0.1:8094 --load
python -m demo.demo --url http://127.0.0.1:8094                  # the narrated demo
python -m benchmarks.run --url http://127.0.0.1:8094             # the 48 questions as Cypher
```

Without `--load` the loader prints the load plan and writes nothing. With it, the loader creates the
indexes in [`schema/dbms_research_kg.cypher`](schema/dbms_research_kg.cypher), loads in about two
to four minutes, and fails unless every label and relationship type holds exactly the planned count.
Give this graph a server of its own.

### Export and import a snapshot

```bash
python -m etl.snapshot export --url http://127.0.0.1:8094   # -> snapshots/dbms-research-kg.sgsnap + manifest.json
python -m etl.snapshot import --url http://127.0.0.1:8095   # into a FRESH server
```

The snapshot (9.5 MB) is shared inside the team with its `manifest.json`, outside git: `snapshots/`
is git-ignored. The manifest records the file's SHA-256, the commit that built it, the engine
version and the count of every label and relationship type, so share the two files together.
Import appends, so `etl.snapshot import` refuses a server that is not empty and checks every count
against the manifest. The snapshot holds the catalog's text and falls under its CC BY 4.0 terms.

### Loader options

| Option | Default | |
|---|---|---|
| `--catalog` | `build/source_catalog.json` | The parsed catalog to load |
| `--url` | `http://localhost:8094` | The Samyama server |
| `--load` | off | Write to the server; without it, print the plan only |
| `--batch-size` | `20` | Nodes per statement; edges go in batches of at most 50 |

---

## Schema

**16 node labels** -- Problem, Topic, Paper, Person, Venue, Institution, Concept, Algorithm, System,
Bound, ComputationModel, Gap, ResearchDirection, FutureDirection, DataSource, TaxonomyTerm

**17 edge types** -- IN_TOPIC, CITES, AUTHORED_BY, APPEARED_AT, RESTS_ON, GENERALIZES, HAS_BOUND,
IN_MODEL, STATE_OF_ART, HAS_GAP, HAS_RESEARCH, CLOSING_REQUIRES, ACTIVE_ON, AFFILIATED_WITH,
RELATED_TO, FROM_SOURCE, CLASSIFIED_AS

| Nodes | | Edges | |
|---|---:|---|---:|
| Person | 4,454 | RELATED_TO (computed) | 8,686 |
| FutureDirection | 3,825 | AUTHORED_BY | 7,000 |
| Paper | 2,679 | CITES | 6,157 |
| ResearchDirection | 2,496 | ACTIVE_ON | 5,536 |
| Bound | 2,106 | STATE_OF_ART | 4,058 |
| Problem | 1,053 | CLOSING_REQUIRES | 3,825 |
| Gap | 1,053 | CLASSIFIED_AS | 3,689 |
| System | 982 | APPEARED_AT | 2,609 |
| Venue | 677 | HAS_RESEARCH | 2,496 |
| Algorithm | 585 | HAS_BOUND | 2,106 |
| Concept | 90 | RESTS_ON | 1,987 |
| Institution | 82 | IN_MODEL | 1,953 |
| TaxonomyTerm | 77 | IN_TOPIC, HAS_GAP, FROM_SOURCE | 1,053 each |
| Topic | 35 | AFFILIATED_WITH | 429 |
| ComputationModel | 16 | GENERALIZES | 31 |
| DataSource | 1 | | |

The paths most questions walk:

```
(Problem)-[:IN_TOPIC]->(Topic)
(Problem)-[:HAS_BOUND]->(Bound)-[:IN_MODEL]->(ComputationModel)
(Problem)-[:HAS_GAP]->(Gap)
(Problem)-[:CITES {role}]->(Paper)-[:AUTHORED_BY]->(Person)
(Person | Institution)-[:ACTIVE_ON]->(Problem)
(Problem)-[:STATE_OF_ART]->(Algorithm | System)
(Problem)-[:RESTS_ON]->(Concept)-[:GENERALIZES]->(Concept)
(Problem)-[:CLOSING_REQUIRES]->(FutureDirection)
(Problem)-[:RELATED_TO {score}]->(Problem)                 computed
```

See [`docs/schema.md`](docs/schema.md) for every property and count.

## Data source

| Source | Supplies | Terms |
|---|---|---|
| [samyama-ai/dbms_research](https://github.com/samyama-ai/dbms_research) at `5fff7f74508a52ac238f3bb608b8c8c872489fec` | 35 topics, 1,053 problem pages, everything in the graph | CC BY 4.0 |

None of it is committed to this repo: `data/` and `build/` are git-ignored.

## Query catalog

The 48 questions of [`docs/scope.md`](docs/scope.md), in
[`benchmarks/scope_questions.cypher`](benchmarks/scope_questions.cypher), with answers and timings
in [`benchmarks/scope_questions.md`](benchmarks/scope_questions.md).

| Group | Questions | About |
|---|---|---|
| A | 1–6 | Problems and topics |
| B | 7–15 | One problem: its references, bounds, gap, who works on it, future work |
| C | 16–22 | Papers |
| D | 23–28 | Researchers and institutions |
| E | 29–34 | Algorithms, systems and bounds |
| F | 35–40 | Connections between problems |
| G | 41–45 | Research opportunities |
| H | 46–48 | Questions the graph must refuse |

**Every answer is checked.** Each question is answered a second time from the raw catalog pages
with plain regexes, without the graph parser (`benchmarks/reference.py`): 17 correct, 8 consistent,
20 answered with a documented limit, 3 refused by design, 0 wrong.

```bash
python -m benchmarks.reference                         # the check, from the raw pages
python -m benchmarks.run --url http://127.0.0.1:8094   # the Cypher, on the loaded graph
```

## MCP server

```bash
python -m mcp_server.server          # read-only tools over MCP, for the engine in mcp_server/config.yaml
```

## Structure

```
etl/
  download_data.py   fetch the catalog at the pinned commit
  source_parser.py   pages -> one JSON catalog
  loader.py          catalog -> nodes and edges; load into an engine
  local_graph.py     build and verify the SQLite graph
  quality.py, audit.py   content criteria; taxonomies, code lists and standards
  snapshot.py        export and import a .sgsnap
schema/              the conformance spec (with the ontology mappings) and the engine indexes
benchmarks/          the 48 questions as Cypher, their raw-page reference, the runner
mcp_server/          the MCP server
demo/                the narrated demo and its GIF
docs/                ontology, taxonomy, schema, standards, provenance, engine notes, reports, logs
tests/               pytest
```

## Documentation

| Document | What it covers |
|---|---|
| [`DATASET_CARD.md`](DATASET_CARD.md) | The dataset in one page: contents, terms, intended use, limits |
| [`docs/ontology.md`](docs/ontology.md) | The classes, the relations between them, the rules that always hold, and the seven vocabulary alignments |
| [`docs/taxonomy.md`](docs/taxonomy.md) | The hierarchies, every coded value with its count, and the id patterns |
| [`docs/schema.md`](docs/schema.md) | Every property and count, and the design decisions |
| [`docs/standards.md`](docs/standards.md) | The six standards groups, codes and identifiers, licences |
| [`docs/data-provenance.md`](docs/data-provenance.md) | The source, its terms, and which parts are our rules |
| [`docs/coding-standards.md`](docs/coding-standards.md) | How code, queries, data and documents are written here |
| [`docs/engine-notes.md`](docs/engine-notes.md) | Engine behaviour and load times |
| [`docs/scope.md`](docs/scope.md) | The 48 questions the graph is built to answer |
| [`docs/quality-report.md`](docs/quality-report.md), [`docs/audit-report.md`](docs/audit-report.md) | The generated quality and standards reports |
| [`docs/phase1-log.md`](docs/phase1-log.md), [`phase2`](docs/phase2-log.md), [`phase3`](docs/phase3-log.md) | How the graph was built, step by step |
| [`docs/schema-conformance-checklist.md`](docs/schema-conformance-checklist.md) | The conformance inventory made before the build |

## Known limits

- **Names are not merged.** A Person is a name as written: "Wang" is many people, and "T. Neumann"
  and "Neumann" are two nodes. No DBLP or ORCID lookup is made.
- **Affiliations are what a page states**, read from brackets such as "Suciu (UW)"; none is
  verified.
- **334 citations do not parse**; their text is kept and no title is made up.
- **Our taxonomies are unreviewed.** Problem types, technique families, model classes and the
  concept hierarchy await a domain reviewer.
- **No vectors.** Similar problems by meaning (question 39) need embeddings, which this build does
  not compute.
- **The catalog is a snapshot of 2026-09-09**, and its pages are synthesized, not expert-verified.

Details are in [`docs/data-provenance.md`](docs/data-provenance.md) and
[`docs/engine-notes.md`](docs/engine-notes.md).

## License

Apache 2.0 for the code. The data is not covered by this licence: the catalog is CC BY 4.0.
