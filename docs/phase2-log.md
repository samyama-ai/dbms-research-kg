# Phase 2 log — reproducible source setup

Tracking issue: #3. Newest entry first.

## 2026-10-15 — Phase 2 implementation review

### Objective

Make the DBMS Research catalog checkout reproducible by pinning its source revision,
providing a downloader that validates the checkout and records its metadata, and
documenting the project setup. The source catalog remains outside the repository in
the git-ignored `data/` directory.

### Implemented

- `etl/download_data.py` clones or updates the catalog at
  `https://github.com/samyama-ai/dbms_research.git`, checks out the pinned revision,
  refuses a non-clone, a clone of another repository, local edits, or a mismatched
  commit, and writes `data/dbms_research.lock.json`.
- The downloader preserves the original fetch time when rerun for the same commit.
  Its lock records repository URL, commit, commit date, fetch time, and count of
  problem Markdown files (excluding topic `README.md` indexes).
- The project metadata in `pyproject.toml` declares runtime dependencies and a `dev`
  extra containing pytest and Ruff. The README's project name, slug, and year fields
  were filled in as part of Phase 2.
- The downloader tests use small local Git repositories, so they do not require a
  network connection.

### Verified source pin and local lock record

The checked-out catalog and lock file were inspected for this log:

| Field | Verified value |
|---|---|
| Repository | `https://github.com/samyama-ai/dbms_research.git` |
| Commit | `5fff7f74508a52ac238f3bb608b8c8c872489fec` |
| Commit date | `2026-09-09T13:15:05+05:30` |
| Fetch time in lock | `2026-10-14T13:02:29+05:30` |
| Problem files | 1,053 |
| Checkout state | At the recorded commit; clean working tree; detached `HEAD` |

The lock file is in git-ignored `data/`, as is the catalog itself. These values
describe the local checkout and lock record; they are not committed with this log.

### Environment and test evidence

At review time, `.venv` exists with Python 3.12.3. From the activated `.venv`,
`python -m pip install -e ".[dev]"` completed successfully: the editable package
was built and installed, with pytest and Ruff already satisfied in the environment.
The installed distribution is `dbms-research-kg` version 0.1.0; pytest 9.1.1 and
Ruff 0.17.0 are available. `pyproject.toml` defines `.[dev]` as the project install
extra.

The final test run used `python -m pytest tests/ -v`; the result is recorded below.

Coverage in the 9 tests consists of 8 downloader tests and 1 smoke test. The
downloader tests cover writing a fresh lock, retaining the fetch timestamp on rerun,
fetching a newer commit and updating the lock, refusing local edits, refusing a
different repository, refusing a non-clone directory, reporting a wrong commit, and
excluding README files from the problem-file count.

### Remaining limitations and unresolved items

**Verified limitations:** the source checkout and lock record remain local and
git-ignored, so a fresh checkout needs to fetch the catalog and regenerate its lock.
The checked-in downloader pins one default commit; changing the source revision
requires an explicit `--commit` and a corresponding update to `PINNED_COMMIT` in the
implementation. The tests exercise the downloader against local fake repositories,
not the remote catalog service.

**Unresolved decisions carried from Phase 1** (also listed in `docs/phase1-log.md` and
`docs/schema.md`): whether v1 uses only the catalog before DBLP enrichment; whether
Problem embeddings are included in v1; who reviews the Concept list and hierarchy;
and whether catalog/snapshot discrepancies should be raised upstream. No decision
about these items is recorded by this Phase 2 implementation.

**Remaining work:** the Phase 2 branch has not been pushed, and no Phase 2 pull
request was found as of this review. Issue #3 remains open for review. These are
workflow steps, not claims that the implementation or source pin is invalid.

### Verification after this log change

`python -m pytest tests/ -v`: **9 passed in 0.61 seconds** (8 downloader tests
and 1 smoke test), run from the activated repository `.venv`.
