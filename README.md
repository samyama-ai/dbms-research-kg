# DBMS Research Knowledge Graph

**{{N}} nodes. {{M}} edges. {{ONE_LINE_SCOPE}} from {{K}} sources.**

![DBMS Research demo](demo/dbms_research.gif)

> Part of the **Samyama** ecosystem — loaded into and queried via the graph engine at [samyama-ai/samyama-graph](https://github.com/samyama-ai/samyama-graph).
> This repo holds the loader and source-data specifics for the KG.

<a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="License"></a>

---

We loaded {{SOURCES}} into one graph, then asked:

> *"{{EXAMPLE_QUESTION}}"*

```cypher
MATCH (a:{{NodeA}})-[:{{REL}}]->(b:{{NodeB}})
RETURN b.name, count(a) AS n
ORDER BY n DESC LIMIT 5
```

**One query across every source.** Powered by [Samyama Graph](https://github.com/samyama-ai/samyama-graph).

---

## Demo

A narrated walkthrough on a fast, real subset.

```bash
python -m demo.demo                                                     # run live
asciinema rec --overwrite --cols 92 --rows 32 --idle-time-limit 2.0 \
  -c "bash -c 'python -m demo.demo'" demo/dbms_research.cast              # re-record
agg demo/dbms_research.cast demo/dbms_research.gif                          # convert to gif
```

---

## Schema

**Node labels** -- {{NODE_LABELS}}
**Edge types** -- {{EDGE_TYPES}}
**Data sources** -- {{SOURCES}}

The historical reference inventory has 12 node labels and 13 relationship types.
The v1 conformance schema adds `Gap`, `ResearchDirection`, `DataSource`,
`TaxonomyTerm`, and the associated relationship types. See [`docs/schema.md`](docs/schema.md),
[`schema/conformance.json`](schema/conformance.json), and
[`schema/dbms_research_kg.ttl`](schema/dbms_research_kg.ttl) for the current
schema artifacts.

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e '.[rdf]'

python -m etl.local_graph build-catalog-candidate \
  --catalog build/source_catalog.json \
  --output build/dbms_research_kg.schema-candidate-v2.sqlite
python -m etl.local_graph verify --graph build/dbms_research_kg.schema-candidate-v2.sqlite
python -m etl.local_graph inspect --graph build/dbms_research_kg.schema-candidate-v2.sqlite
python -m etl.local_graph traverse \
  --graph build/dbms_research_kg.schema-candidate-v2.sqlite \
  --problem 01-relational-theory/acyclic-join-dependencies
python -m etl.loader --catalog build/source_catalog.json  # source-only dry run
```

The existing artifact `build/dbms_research_kg.sqlite` is preserved as a
12-label/13-type snapshot-derived graph (20,019 nodes, 40,189 relationships).
The v1 candidate command writes a different file and uses only the pinned source
catalog because the `.sgsnap` records do not carry enough per-record source paths
to meet v1 provenance requirements. It is idempotent for identical input and
implementation hashes, resumes only its own matching candidate, and refuses to
overwrite unrelated SQLite files. It uses embedded SQLite; it needs no Docker or
graph service.

The verified catalog candidate currently has 19,676 nodes and 41,916 unique
relationships, 16 declared labels and 17 declared relationship types (15 labels
and 15 relationship types populated). `Institution`, `AFFILIATED_WITH`, and
`GENERALIZES` are empty because the pinned catalog does not support those claims.
Its `RELATED_TO` edges are recomputed from pairs sharing at least two distinct
cited papers/concepts. The candidate has fewer nodes than the snapshot artifact;
it does not copy snapshot-only records with unverified lineage. These counts are
not a claim of complete acceptance: the candidate passes six ontology alignment
checks, while CiTO remains partial because the `artifact` role mapping is
unresolved. The original snapshot graph remains a separate legacy artifact and
does not conform to the v1 label/relationship inventory.

`python -m etl.local_graph verify` reports graph integrity, Turtle validation,
and a separate status for each alignment. The 48-question acceptance suite is
intentionally deferred.

`etl.loader` remains the source-catalog preparation and remote Samyama loader;
its default invocation only prints a dry-run plan. Do not use its remote `--load`
mode to build the local SQLite artifact. See [`docs/phase3-log.md`](docs/phase3-log.md)
and [`docs/schema-conformance-checklist.md`](docs/schema-conformance-checklist.md)
for conformance results and limitations.

## Structure
```
etl/          # downloaders + graph loader
schema/       # cypher schema / ontology
mcp_server/   # MCP server exposing the KG
demo/         # narrated demo (cast + gif)
benchmarks/   # benchmark queries
docs/         # design + source notes
tests/        # pytest
pyproject.toml
```

---
## Using this template
1. Click **Use this template** (this repo is a Gitea template) and name your repo `<domain>-kg`.
2. Find-and-replace the `{{...}}` placeholders (KG_NAME, KG_SLUG, NODE_LABELS, EDGE_TYPES, SOURCES, N, M, K, example query).
3. Rename `schema/template_kg.cypher` -> `schema/<slug>_kg.cypher` and fill in real node/edge definitions.
4. Implement the `etl/` downloaders + loader and the `mcp_server/` tools for your domain.
5. Add the repo to the **samyama-graph** team.

### Placeholder reference
| Placeholder | Meaning |
|-------------|---------|
| `{{KG_NAME}}` | Human name, e.g. "Drug Interactions" |
| `{{KG_SLUG}}` | file/id slug, e.g. "druginteractions" |
| `{{NODE_LABELS}}` / `{{EDGE_TYPES}}` | comma-separated schema |
| `{{SOURCES}}` | data sources + licenses |
| `{{N}}`/`{{M}}`/`{{K}}` | node/edge/source counts |
| `{{EXAMPLE_QUESTION}}` / `{{NodeA}}`/`{{REL}}`/`{{NodeB}}` | hero query |
