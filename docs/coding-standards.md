# Coding standards

How code, queries, data and documents are written in this repo.

Most rules below are enforced by a linter, a validator or a test, and say which. A rule marked
*by review* has no check behind it.

## Before you push

```bash
ruff check .
python -m pytest -q
```

Both must pass. The tests need no running server. Tests that need the catalog checkout
(`data/dbms_research`) or a build (`build/`) skip themselves where those are absent; run
`python -m etl.download_data` and the build of the [README](../README.md) to run them all.

## Python

| Rule | Enforced by |
|---|---|
| Python 3.10 or later | `pyproject.toml` |
| Lines are at most 120 characters | ruff `E501` |
| Imports are sorted, standard library first | ruff `I` |
| No unused imports or variables | ruff `F` |
| No mutable default arguments | ruff `B` |
| A module starts `from __future__ import annotations` | by review |
| Every module has a docstring that says what it is for and how to run it | by review |
| No file over 500 lines, so a reviewer can read it in one pass | by review |

The ruff rule sets are `E`, `F`, `W`, `B` and `I`; `E731` is ignored, because a one-line lambda for
a lookup reads better than a two-line `def`.

### Comments and docstrings

Say **why**, not what. A comment earns its place by recording something the code cannot: a
measurement, a trap, a decision.

```python
# Good: records a measurement nobody could guess.
# Endpoints matched inside UNWIND do not use the index: about 9 s per 100 edges. Literal
# MATCH ... WHERE ... MERGE in batches of 50 takes about 0.01 s a batch.

# Not needed: repeats the code.
# Loop over the problems.
```

## Naming

| Thing | Style | Example |
|---|---|---|
| Node label | `PascalCase`, singular | `FutureDirection` |
| Edge type | `UPPER_SNAKE_CASE`, a verb phrase read from source to target | `CLOSING_REQUIRES` |
| Property | `snake_case` | `last_reviewed` |
| Property recording how a value was decided | ends `_method` | `verdict_method` |
| Coded value | `kebab-case` text, as the catalog writes its statuses | `partially-solved` |
| Node id | see [`taxonomy.md`](taxonomy.md#identifiers) | `paper:abda98318c49f98b20a0adf5` |
| Benchmark question | `Q` and its number in [`scope.md`](../benchmarks/scope.md) | `Q21` |
| Python function, variable | `snake_case` | `merge_identities` |
| Python constant | `UPPER_SNAKE_CASE` | `CONCEPT_HIERARCHY` |

## Building nodes and edges

| Rule | Enforced by |
|---|---|
| Every node has `id`, `provenance`, `source`, `method`, `retrieved_at`, `source_date`, `source_url` | `etl.conformance.validate` |
| Every edge has `source` and `source_url` | `etl.conformance.validate` |
| A coded property holds only a value on its list in `schema/conformance.json` | `etl.conformance.validate` |
| An edge joins only the labels its relation allows, and both ends exist | `etl.conformance.validate` |
| Ids are unique across the graph and deterministic for the same commit | `etl.conformance.validate`; tests |
| `retrieved_at` and `source_date` come from the lock record, never the clock | `etl.conformance.validate` |
| A missing value is left out when it is sent to the engine, not written as `''` | `etl.records.cypher_map`; test |

## Source data

| Rule | Enforced by |
|---|---|
| One source: the catalog at the pinned commit | `etl.download_data` refuses any other commit |
| Nothing downloaded or built is committed; `data/`, `build/` and `snapshots/` are git-ignored | `.gitignore` |
| Values are kept as written. Names are not corrected, merged or looked up. | by review |
| A list (concepts, institutions, models) is reviewable code in `etl/source_entities.py` | by review |
| A value decided by our rule records the rule (`*_method`, `evidence`, `evidence_status`) | `etl.conformance.validate`; `etl.audit` |
| Something left out is counted, never silently dropped | `etl.quality` |
| No external lookup (DBLP, ORCID, citation counts) | by review |

## Cypher

| Rule | Reason |
|---|---|
| String literals use double quotes | they work on every engine version used here |
| Under a `LIMIT`, the `ORDER BY` ends with a column that breaks ties | without one, tied rows come back in any order and the `LIMIT` cuts at random |
| An absent identifier is tested with `<> ""`, an absent year with `IS NULL` | that is how each is stored; see [`ontology.md`](ontology.md#rules), rule 6 |
| Follow edges in the direction the ontology gives | the engine's BFS follows edge direction |

Statements the loader sends are built by `etl.records.cypher_literal` and `cypher_map`. Do not build
a literal by hand.

## Queries

The benchmark is [`benchmarks/scope_questions.cypher`](../benchmarks/scope_questions.cypher). A
question is in it only when:

| Rule | Enforced by |
|---|---|
| Its header is `// Q<n> · <question>`, with `n` the number in `benchmarks/scope.md` | `tests/test_benchmarks.py` |
| It runs without error on the loaded graph | `python -m benchmarks.run` |
| Its answer is also computed from the raw pages, without the graph parser | `benchmarks/reference.py` |
| The two agree, or the limit of the answer is documented and holds | `python -m benchmarks.reference` (verdict never `WRONG`) |
| A question the graph must refuse returns no rows | `python -m benchmarks.run` |

The reference is written from the question and the raw page, not from the Cypher, so a mistake in
one is not copied into the other.

## Tests

| Rule |
|---|
| Unit tests run on small made-up records written in the test itself, never on a download |
| A test that needs the catalog or a build skips itself where they are absent |
| A check that can only pass is not a test. Each checker has a test that proves it can fail. |
| Do not assert a wall-clock time |

## Documents

| Rule | Enforced by |
|---|---|
| A number quoted in a document comes from a build, not from memory | `tests/test_docs_match_data.py` for the counts |
| Labels and edge types are listed in the same order everywhere | `tests/test_docs_match_data.py` |
| Every coded value in `schema/conformance.json` is listed in `docs/taxonomy.md` | `tests/test_ontology_docs.py` |
| A document describes the repo as it is; how it got there goes in the commit message and the PR | by review |
| A value that is our rule, not the page's, is labelled as such | by review |
| A limit is stated next to the claim it limits | by review |
| No tool or model credit lines in documents or commits | by review |

## Changing the schema

A label, edge type or coded value is declared in several places. Change all of them in one commit;
the tests fail until they agree.

| Change | Files |
|---|---|
| Label or edge type | `schema/conformance.json`, `schema/dbms_research_kg.cypher`, the builder in `etl/`, `README.md`, `DATASET_CARD.md`, `docs/schema.md`, `docs/ontology.md` |
| Coded value | `schema/conformance.json`, `docs/taxonomy.md` |
| Mapping to another vocabulary | `ontology_mapping_triples` in `schema/conformance.json`, `docs/ontology.md` |
| Benchmark question | `benchmarks/scope.md`, `benchmarks/scope_questions.cypher`, `benchmarks/reference.py` |

## Safety

| Rule |
|---|
| Load or import into a server of its own. Snapshot import appends, so import only into an empty server. |
| Never write to a server that holds another graph. |
| No secret, key or token belongs in this repo. The source needs none. |
