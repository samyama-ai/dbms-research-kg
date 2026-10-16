# DBMS Research Knowledge Graph

A knowledge graph of the 1,053 open problems in the
[DBMS Research catalog](https://github.com/samyama-ai/dbms_research) (35 topics), built
for [Samyama Graph](https://github.com/samyama-ai/samyama-graph).

> **Status: Phase 2 (project setup).** The graph itself is built in later phases; this
> README is updated with counts, schema and an example query when the graph exists.

<a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-blue" alt="License"></a>

## Source data

The catalog is fetched at a pinned commit, never edited, and kept out of git:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m etl.download_data            # clones into data/dbms_research and writes data/dbms_research.lock.json
python -m etl.download_data --commit 5fff7f74   # a full or short SHA; update PINNED_COMMIT to keep it
pytest
```

The lock file records the repository, commit, commit date, fetch time and the number of
problem pages. Rerunning on the same commit keeps the original fetch time.

## Documents

- [docs/scope.md](docs/scope.md): the 48 questions the graph must answer
- [docs/schema.md](docs/schema.md): the planned schema
- [docs/phase1-log.md](docs/phase1-log.md), [docs/phase2-log.md](docs/phase2-log.md): work logs

## Structure

```
etl/          # downloader (and, later, the graph builder)
schema/       # schema files
mcp_server/   # MCP server exposing the KG
demo/         # demo (added with the graph)
benchmarks/   # benchmark queries
docs/         # design notes and logs
tests/        # pytest
```

Data source licence: CC BY 4.0 (the catalog). Code licence: Apache 2.0.
