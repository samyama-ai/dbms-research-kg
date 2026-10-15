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
The available local graph source is the `dbms-research.sgsnap` export, whose
SHA-256 is checked by the builder. See [`docs/schema.md`](docs/schema.md),
[`schema/conformance.json`](schema/conformance.json), and
[`schema/dbms_research_kg.ttl`](schema/dbms_research_kg.ttl) for the current
schema artifacts.

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .

python -m etl.local_graph build \
  --snapshot /home/vm/dbms-research.sgsnap \
  --catalog build/source_catalog.json \
  --output build/dbms_research_kg.sqlite
python -m etl.local_graph verify --graph build/dbms_research_kg.sqlite
python -m etl.local_graph traverse \
  --graph build/dbms_research_kg.sqlite \
  --problem 01-relational-theory/acyclic-join-dependencies
python -m etl.loader --catalog build/source_catalog.json  # source-only dry run
python -m pytest -q
```

`etl.local_graph` uses Python's built-in SQLite support; it needs no Docker or
graph service. It imports the verified local snapshot without changing it,
collapses repeated same-type endpoint pairs while retaining duplicate snapshot
edge IDs/property variants, then adds source-backed citation/authorship/SOTA
edges and `RELATED_TO` edges for problem pairs sharing at least two mapped
papers/concepts. The output is a persistent property-graph artifact at
`build/dbms_research_kg.sqlite`. Re-running the build with the same inputs is
idempotent and resumes interrupted work; an existing artifact from different
inputs is never overwritten. The snapshot contains no source commit identifier,
so this build preserves it as snapshot-origin data and marks added edges with the
pinned catalog commit. The local artifact does not prove equivalence with any
currently running graph service.

Verified local artifact: **20,019 nodes**, **40,189 unique directed edges**,
12 labels and 13 relationship types. The snapshot had 39,393 edge records but
3,447 repeated typed endpoint pairs; those were coalesced with source edge IDs
and conflicting properties retained. The pinned catalog contributed 1,074
additional mapped relations and 3,169 `RELATED_TO` pairs meeting the shared
evidence threshold. The resulting edge total exceeds 39,400 without placeholder
nodes or arbitrary links.

`etl.loader` remains the source-catalog preparation and remote Samyama loader;
its default invocation only prints a dry-run plan. Do not use its remote `--load`
mode to build the local SQLite artifact. See [`docs/phase3-log.md`](docs/phase3-log.md)
for source extraction limitations.

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
