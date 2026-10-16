# Phase 3 — source catalog mapping and resumable loader

> Historical implementation notes below are superseded by the current status
> section at the end. In particular, port 8093 is protected and the old load
> example must not be run.

The loader uses the local catalog from upstream commit
`5fff7f74508a52ac238f3bb608b8c8c872489fec`. It does not fetch bibliographic
records or write to the reference graph.

## Implemented node types

`Topic`, `Problem`, `Paper`, `Person`, `Venue`, `Bound`, `FutureDirection`,
`Algorithm`, `System`, `Concept`, and `ComputationModel` (11 of the reference
schema's 12 node types). Algorithm, System, Concept, and ComputationModel mentions
must match the explicit term lists in `etl/source_entities.py` and occur in the
appropriate source section. `Institution` extraction remains unimplemented because
the source does not support reliable affiliation claims.

Citation records retain normalized raw citation text and the source page path.
Title, author strings, venue text, year, DOI, and URL are extracted only from
explicit delimiters and patterns. Uncertain title parses are marked `uncertain`;
source-page unverified flags are kept distinct from bibliographic verification.
`source_verified` remains false because no independent source was checked.

## Implemented relationship types

`IN_TOPIC`, `HAS_BOUND`, `CLOSING_REQUIRES`, `CITES`, `AUTHORED_BY`,
`APPEARED_AT`, `STATE_OF_ART`, `RESTS_ON`, and `IN_MODEL` (9 of 13). The loader
maps the schema directions and endpoint labels, including `Paper → Person`,
`Paper → Venue`, and `Problem → Paper`.

Still missing: `ACTIVE_ON`, `AFFILIATED_WITH`, `GENERALIZES`, and `RELATED_TO`.
The source does not justify verified affiliations. Activity and concept hierarchy
extraction need stronger source rules; `RELATED_TO` is computed and deferred.

## Identity and resume audit

Paper identity uses DOI when present, otherwise normalized title and year, with
normalized citation text as the uncertain-parse fallback. To preserve compatibility
with the existing graph, the representative ID is the legacy full-citation ID of
the first matching citation in deterministic catalog order. A read-only preflight
checks that every representative ID exists with the expected citation identity.
The catalog dry run produces 2,988 canonical Paper identities.

A read-only audit of port 8093 found 5,273 legacy Paper nodes. Their citation text
groups into 2,988 canonical identities, leaving 2,285 alternate-form Paper nodes
already present. The loader maps citations to representatives and does not delete
or recreate those existing nodes. The graph currently has 1,053 `IN_TOPIC` edges
and 40 `HAS_BOUND` edges; endpoint `MERGE` makes replay safe for those edges.

The dry run plans 16,111 canonical node records and 27,627 relationship records.
Because 2,285 legacy Paper aliases are already stored, the projected physical
graph count after resume is 18,396 nodes and 27,627 edges. Existing alias nodes
remain; this count is based on the read-only 8093 label/edge audit and current
dry-run endpoint sets.

The corrected citation parser produces 5,267 Person identities and 9,996
`AUTHORED_BY` edges, compared with 5,193 and 10,178 in the reference snapshot. A
read-only normalized-name comparison overlaps on 3,534 names (1,733 source-only,
1,657 reference-only). The previous 6,435/16,933 result included incorrect
splitting of surname/initial formats and leaked bold role markup. Remaining
differences reflect unresolved name variants and intentionally omitted uncertain
author syntax; no external identity resolution is used. These totals are not target
counts.

Other parser limits: venue names are retained as raw strings; multi-year ranges
use the first year; citation metadata is source-parsed rather than verified; and
unmatched author-name variants remain separate Person IDs.

`MERGE` prevents new duplicate nodes by stable ID and new duplicate relationships
by typed endpoint pair. Existing alternate Paper nodes remain in place. The loader
does not reconcile other legacy node IDs or remove existing duplicate edges.

### FutureDirection recovery

The prior source version generated FutureDirection IDs using a zero-based
`enumerate()` index. A later loader change started that index at 1, so `MERGE` did
not match any of the existing FutureDirection IDs and created one shifted-ID copy
per source item. The loader now uses the original zero-based index. The read-only
8093 audit confirmed that all 3,825 source items have exactly one zero-based node
and one index-shifted duplicate, with matching `problem_id`, `text`, and
`source_path`; no unexpected IDs or properties were found. None of the shifted
duplicates has an incident relationship.

`etl/repair_future_directions.py` verifies each candidate against the pinned source,
checks all incident edges, and defaults to read-only mode. The approved repair
would delete only the 3,825 shifted IDs, leaving 3,825 canonical nodes and the
existing 1,093 edges. It does not create relationships. After repair, rerunning the
loader uses the same canonical IDs and endpoint `MERGE` for relationships.

Read-only repair plan:

```bash
python -m etl.repair_future_directions --catalog build/source_catalog.json --url http://localhost:8093
```

Deletion requires adding `--apply` after approval.

## Commands

Validate the source catalog and show counts without connecting to a graph:

```bash
python -m etl.loader --catalog build/source_catalog.json
```

After review and explicit approval, load or resume only the new graph:

```bash
python -m etl.loader --catalog build/source_catalog.json --url http://localhost:8094 --load
```

Do not run this command until an isolated clone on 8094 has been created and
verified and the operator has approved live writes. The loader now refuses
`--load` on ports 8092 and 8093.

## Current implementation status (2026-10-15)

The machine-readable inventory now defines 16 node labels and 17 relationship
types (including `TaxonomyTerm`, `CLASSIFIED_AS`, `Gap`, `ResearchDirection`,
`DataSource`, `HAS_GAP`, `HAS_RESEARCH`, `ACTIVE_ON`, and `FROM_SOURCE`). The
offline catalog dry run reports 19,730 planned node records and 38,014 planned
edge records. These are source-derived plan counts, not counts in either live
graph and not a target to force.

Latest counts by type are available by running `python -m etl.loader` with the
pinned catalog. Current gaps are material: `Institution`, `AFFILIATED_WITH`,
`GENERALIZES`, and `RELATED_TO` are empty; only a small allow-listed subset of
algorithms, systems, concepts, and models is extracted; bibliography parsing is
not external verification; person identity variants are not resolved; and
current-research person matching is a conservative exact normalized-name rule.
These gaps mean full schema/query conformance is not established. The 48-question
module has an explicit dispatch/status policy and refusal behavior, but its
current tests do not validate each question against a full known-answer fixture.

The loader default target is `http://localhost:8094`; a dry run never connects
to a graph. No live graph writes were performed in this implementation pass.

## Source-only schema candidate (2026-10-15)

Preserved the pre-refinement SQLite artifact at
`build/dbms_research_kg.preconformance-backup-20261015.sqlite`. The backup was
opened read-only and passed `PRAGMA integrity_check`; its logical totals match
the original (20,019 nodes, 40,189 relationships). The SQLite files have
different SHA-256 hashes because the backup API rewrites the database pages;
the original file was not modified.

Built a separate, pinned-catalog-only candidate at
`build/dbms_research_kg.schema-candidate-v2.sqlite` using:

```bash
python -m etl.local_graph build-catalog-candidate \
  --catalog build/source_catalog.json \
  --output build/dbms_research_kg.schema-candidate-v2.sqlite
python -m etl.local_graph verify \
  --graph build/dbms_research_kg.schema-candidate-v2.sqlite
```

Fresh-process verification reports 19,676 nodes, 41,916 relationships, zero
duplicate logical identities, zero missing endpoints, zero endpoint-type
errors, zero provenance errors, zero schema-data errors, and SQLite integrity
`ok`. A repeated build against the same candidate signature returned the same
totals. The candidate declares 16 labels and 17 relationship types; it
populates 15 labels and 15 types. `Institution`, `AFFILIATED_WITH`, and
`GENERALIZES` are empty because the pinned catalog does not supply evidence
for them. `ontology_validation` remains `NOT VERIFIED` because `rdflib` is not
installed. This candidate is not a refined copy of the snapshot-backed graph:
it excludes snapshot records whose individual source lineage cannot be
verified against the pinned catalog.

Read-only identity-key comparison against the previous graph reports nodes:
old 20,019, candidate 19,676, 18,623 candidate keys added, 18,966 old keys
removed, 1,053 common keys with changed properties; relationships: old
40,189, candidate 41,916, 38,985 candidate keys added, 37,258 old keys
removed, 2,931 common keys with changed properties. These are key-set diffs,
not semantic add/remove counts: the old snapshot and catalog candidate use
different logical-ID schemes for many records.

The focused builder/conformance tests passed (`29 passed`). The 48-question
acceptance suite was not run. A representative candidate traversal returned
paper `Constraint Solving via Fractional Edge Covers.` and two linked authors,
plus a related problem connected by two shared source-evidence items. Full
ontology semantics and human approval of heuristic taxonomy definitions remain
open; no full-conformance claim is made.

## Ontology reconciliation and v1 candidate audit (2026-10-16)

Confirmed `docs/schema.md` v1.0 as the target; the default `.sgsnap` build path
still imports the historical 12-label/13-type snapshot. The source-only v1
candidate is the single migration target; no new candidate database was created.
The original graph and existing candidate artifacts were preserved. The backup
`build/dbms_research_kg.preconformance-backup-20261015.sqlite` was compared
read-only with the original: all rows in `graph_metadata`, `nodes`, and `edges`
match, and both pass `PRAGMA integrity_check`.

The v1 machine inventory now records the complete required ontology mapping
triples and datatype-property declarations. The Turtle explicitly labels
PROV/source-time and `CLASSIFIED_AS` mappings as non-entailing field
correspondences, and maps Topic `number` to `skos:notation` in the correct
direction. `validate_ontology()` uses rdflib 7.6.0 in the project `.venv` and
passes 183 parsed triples, including all class/property contracts, domains,
ranges, data-property declarations, mapping triples, and CiTO role annotations.
No RDF instance serialization is required by the project LPG architecture.

`validate_sqlite_alignments()` was added and run read-only against both graphs.
Legacy graph statuses: project domain FAIL, PROV-O PARTIAL, SKOS PARTIAL,
Dublin Core Terms PASS, FOAF PASS, Schema.org PASS, CiTO PARTIAL. V1 candidate
statuses: project domain PASS, PROV-O PASS, SKOS PASS, Dublin Core Terms PASS,
FOAF PASS, Schema.org PASS, CiTO PARTIAL. The unresolved item is the mapping
for the two `artifact` citation roles. Candidate `mixed` and `unclassified`
roles remain local values without a CiTO assertion.

The existing candidate has 19,676 nodes and 41,916 edges (16 schema labels and
17 relationship types declared; 15 labels/types populated). Verification found
zero duplicate logical nodes/edges, endpoint errors, missing required
properties, provenance errors, or schema-data errors; SQLite integrity is
`ok`. Its data rows were not rebuilt or changed. The builder safely refreshed
metadata only after exact row-by-row comparison to freshly prepared catalog
output; a second build retry retained the same counts. The legacy original
remains 20,019 nodes and 40,189 edges with 12 labels and 13 types.

Focused tests: `./.venv/bin/python -m pytest -q tests/test_conformance.py tests/test_loader.py`
→ 34 passed. `git diff --check` passed. The 48-question
suite was not run. Full seven-alignment conformance is not claimed until the
project owner resolves the CiTO `artifact` role semantics.

Tests:

```bash
python -m pytest -q
```

## V4 CiTO resolution and verification (2026-10-16)

The two source-tagged `artifact` citations have distinct meanings. The
ClockBound citation identifies a software/time service and now maps to generic
`cito:cites`, with a rationale noting that CiTO has no software-specific
property. The CEB citation identifies a benchmark/workload and maps to
`cito:citesAsDataSource`. Both edges retain `role=artifact` and `role_raw`.
The loader selects these mappings by the catalog-cited URL; unknown artifact
URLs use generic `cito:cites` with an explicit fallback note. Prepared-data and
SQLite validators check the mapping and rationale.

The v4 candidate was built at
`build/dbms_research_kg.schema-candidate-v4.sqlite` from the pinned catalog.
All 105 tests pass, the Turtle ontology validator passes, and persisted CiTO
validation reports zero invalid mappings. The v4 graph has 19,655 nodes and
41,761 edges; thus it remains 345 nodes below the requested 20,000-node
minimum while exceeding the edge minimum by 1,761. The original graph contains
snapshot-only Institution/affiliation and hierarchy records without
per-record pinned-catalog provenance, so they were not imported. The pinned
catalog contains no verified Institution records or reviewed concept hierarchy
pairs. No records were added to reach a numeric target.

Verification command:

```bash
./.venv/bin/python -m etl.local_graph verify --graph build/dbms_research_kg.schema-candidate-v4.sqlite
```

The 48-question tests pass as part of the full suite, but this phase did not
reassess their answer correctness independently. The original graph and
candidate v2/v3 remain unchanged.

## 2026-10-16 — AI review of PR #8 addressed here; PR #8 closed

**Who:** Krithi, with Claude. PR #8 (`feat/local-kg-builder`) added `etl/local_graph.py`,
which imports `etl/citations.py` and the catalog `prepare()` that only exist on this
branch, so #8 could not run on its own. #8 is closed; its review points (review 19154)
are fixed on this branch:

| Point | Fix |
|---|---|
| `etl/local_graph.py` 574 lines (> 500) | split: the legacy `.sgsnap` importer moved to `etl/snapshot_graph.py`; also `etl/loader.py` → `records.py`, `finalize.py`, `engine_load.py` and `etl/conformance.py` → `alignments.py`. All files < 500 lines; old imports still work. Rebuilding onto a copy of candidate v4 was accepted, so the output is unchanged |
| `download_data.py`: short SHA, blanket fetch fallback, missing `origin`, option-like `--commit` | fixed in PR #4 and merged here |
| `mcp_server/config.yaml`: tenant mismatch; `host`/`port` unread | config now has the engine `url` (read by `mcp_server/server.py`) and `snapshot_tenant: dbms-research`, matching the published snapshot. The engine serves one graph per instance, so no tenant is passed to queries. Two real read-only tools replace the stub |
| README: broken links, machine-specific path, placeholders, missing demo commands | README rewritten: no placeholders, only links to files on this branch, `~/dbms-research.sgsnap` as the documented default, no demo commands until a demo exists |
| `docs/phase2-log.md` points | fixed in PR #4 and merged here |
