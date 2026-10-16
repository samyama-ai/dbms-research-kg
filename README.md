# DBMS Research Knowledge Graph

A knowledge graph of the 1,053 open problems in the
[DBMS Research catalog](https://github.com/samyama-ai/dbms_research) (35 topics), built
for [Samyama Graph](https://github.com/samyama-ai/samyama-graph). Every node and edge is
read from the catalog at a pinned commit and carries its source page.

<a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="License"></a>

## Build

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,rdf]"
python -m etl.download_data                       # catalog at the pinned commit -> data/
python -m etl.source_parser                       # pages -> build/source_catalog.json
python -m etl.local_graph build-catalog-candidate \
  --catalog build/source_catalog.json \
  --output build/dbms_research_kg.schema-candidate.sqlite
python -m etl.local_graph verify --graph build/dbms_research_kg.schema-candidate.sqlite
python -m pytest -q
```

The candidate is a SQLite property graph built only from the pinned catalog. `verify`
checks the schema, identifiers, edge endpoints, provenance and the seven ontology
alignments. A rebuild with the same inputs gives the same graph; an existing file built
from different inputs is never overwritten.

`python -m etl.loader --catalog build/source_catalog.json` prints a dry-run load plan
for a Samyama engine. It writes nothing without `--load`.

### The 2026-09 reference graph

`python -m etl.local_graph build --snapshot <path to dbms-research.sgsnap>` imports the
published 2026-09 snapshot (`kg-snapshots-v10`, checksum verified) into its own SQLite
file for comparison. The default path is `~/dbms-research.sgsnap`. That graph keeps
snapshot provenance and is not the catalog-built candidate.

## Schema and standards

- [docs/schema.md](docs/schema.md): node labels, edge types, provenance, code lists
- [docs/standards.md](docs/standards.md): 7 ontology alignments, 4 taxonomies, 12 code lists, 6 standards
- [schema/conformance.json](schema/conformance.json): the machine-checked schema
- [schema/dbms_research_kg.ttl](schema/dbms_research_kg.ttl): the ontology (Turtle)
- [docs/scope.md](docs/scope.md): the 48 questions the graph must answer
- Logs: [phase 1](docs/phase1-log.md), [phase 2](docs/phase2-log.md), [phase 3](docs/phase3-log.md)

## Structure

```
etl/          # download, parse, build, check
schema/       # conformance spec and ontology
mcp_server/   # MCP server exposing the KG
benchmarks/   # benchmark queries
docs/         # design notes and logs
tests/        # pytest
```

Data source licence: CC BY 4.0 (the catalog). Code licence: Apache 2.0.
