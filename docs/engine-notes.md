# Engine notes

What was observed about the Samyama engine while building and loading this graph, what this repo
does about it, and what was not tested.

**Engines used**, on Linux x86_64, observed 2026-10-14 to 2026-10-16:

| Engine | Image | Used for |
|---|---|---|
| Samyama Graph 1.11.0 | `ghcr.io/samyama-ai/samyama-graph:latest` | loading, the benchmark, the demo GIF, snapshots |
| Samyama Graph 1.7.1, licensed build | `samyama:1.7.1-internal-licensed` | the console's algorithms, natural-language queries and vector search, for the long demo |

## Behaviour that shaped the loader

| Behaviour | What this repo does |
|---|---|
| Matching edge endpoints inside `UNWIND` does not use an index: about 9 s per 100 edges, and a full load died on an HTTP timeout | `schema/dbms_research_kg.cypher` creates an `id` index per label before the load, and each batch of 50 edges is written as literal `MATCH … WHERE … MERGE` statements: about 0.01 s per batch, and still idempotent |
| A property written as `''` is an empty string, not null | `etl.records.cypher_map` leaves a missing value out. Before this, 364 paper years were `""` on the engine and sorting by year failed |
| Snapshot import appends to whatever the server holds | `python -m etl.snapshot import` refuses a server that is not empty, and checks every count against the manifest after import |
| The schema file uses `CREATE INDEX ON :Label(prop)`, not uniqueness constraints | ids are made unique by the build, and `etl.local_graph verify` refuses a duplicate before anything is sent |
| A failed import leaves the server half-loaded, and there is no transaction to roll back | `etl.snapshot import` says to recreate the container, the only clean recovery |

The loader fails unless every label and relationship type on the engine holds exactly the count it
planned.

## Behaviour on the licensed 1.7.1 build

Seen while preparing the long demo; none of it affects the load.

- `POST /api/algorithm` (PageRank, components, BFS) exists only on the licensed build; the public
  image answers 404.
- BFS follows edge direction. A Topic cannot reach its own problems, because IN_TOPIC points from
  the problem to the topic.
- `UNWIND … SET` is refused, so vectors are written node by node, after one `CREATE VECTOR INDEX`
  per label.
- Natural-language queries run only on a named tenant, and stop after 60 seconds. A local 7B model
  through Ollama needs two warm-up calls to stay under that.
- Ollama serves one embedding request at a time; parallel requests time out in its queue, so
  embedding runs with one worker.

## Not tested

- Whether the `graph` parameter or a tenant keeps two graphs apart on one server. Give this graph a
  server of its own, and import its snapshot only into an empty one.
- Behaviour on engines older than 1.7.1.

## Load performance

Measured on 1.11.0 with the full graph, 20,211 nodes and 53,721 edges:

| Step | Time |
|---|---|
| `python -m etl.local_graph build-catalog-candidate` (SQLite, no engine) | about 15 s |
| `python -m etl.loader --load` (indexes, nodes, edges, count check) | 150 to 260 s, depending on what else the machine is running (262 s on 2026-10-16) |
| `python -m etl.snapshot import` of the 9.5 MB `.sgsnap`, with its count check | 1.3 s |

## Query performance

The 47 Cypher queries of the benchmark ([`benchmarks/scope_questions.md`](../benchmarks/scope_questions.md))
each return in 1 to 57 ms on 1.11.0, half of them in 3 ms or less. One machine, one run: treat these
as an order of magnitude, not a benchmark result.
