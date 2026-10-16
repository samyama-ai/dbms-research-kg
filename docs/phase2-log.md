# Phase 2 log — reproducible source setup

Tracking issue: #3 (PR #4). Newest entry first.

## 2026-10-16 — AI review of PR #4 (review 19146)

**Who:** Krithi, with Claude. All points addressed:

| # | Point | Fix |
|---|---|---|
| 1 | `--commit` failed for a short SHA | the argument is resolved to the full SHA (`git rev-parse --verify <c>^{commit}`) before checkout and comparison; tests for a short SHA and an option-like value |
| 2 | PR description claimed the lock file and dev dependencies were added | description corrected: the lock is git-ignored, only `name` and `description` changed in `pyproject.toml` |
| 3 | stale "not pushed / no PR" statement | removed (see the status below) |
| 4 | README linked missing files and kept template placeholders | README rewritten for Phase 2: no placeholders, no links to files that do not exist yet |
| 5 | a lock from another repo was reused | the lock is reused only for the same commit **and** repo |
| 6 | the fetch fallback caught every checkout failure and missed unadvertised commits | the commit is looked up locally, then after `git fetch origin`, then by `git fetch origin <commit>`; otherwise a clear `CatalogError` |
| 7 | a missing `git` binary gave a traceback | `main` prints "git is not installed or not on PATH" and exits 1 |
| — | tests | the wrong-repo test matches "is a clone of"; new tests for short SHA, option-like commit, unknown commit, lock from another repo, missing `origin`, and `main` exiting 1 with a readable message (15 tests) |
| — | the "1,053 problems" comment next to `PINNED_COMMIT` would go stale | dropped |


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

*Point-in-time evidence from 2026-10-15; versions and timings will differ on another machine.*
At review time, `.venv` exists with Python 3.12.3. From the activated `.venv`,
`python -m pip install -e ".[dev]"` completed successfully: the editable package
was built and installed, with pytest and Ruff already satisfied in the environment.
The installed distribution is `dbms-research-kg` version 0.1.0; pytest 9.1.1 and
Ruff 0.17.0 are available. `pyproject.toml` defines `.[dev]` as the project install
extra.

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

**Status:** the branch is pushed as PR #4; issue #3 stays open until it merges.

### Test result

On 2026-10-15, `python -m pytest tests/ -v` gave **9 passed** (8 downloader tests and
1 smoke test). After the review fixes of 2026-10-16: **15 passed** (14 downloader
tests and 1 smoke test).
