"""Fetch the dbms_research catalog into ./data/dbms_research at a pinned commit.

    python -m etl.download_data                 # clone or update, check out PINNED_COMMIT
    python -m etl.download_data --commit <sha>  # a different commit (then update PINNED_COMMIT)

Running it twice gives the same files. The commit is pinned so that a rebuild
gives the same graph. The script stops with an error when:

- data/dbms_research exists but is not a git clone,
- it is a clone of some other repo,
- it has local changes (they would silently change the graph),
- or it is not at the requested commit after checkout.

Each fetch is recorded in data/dbms_research.lock.json: repo, commit, commit
date, fetch time and number of problem pages. The lock is kept as long as the
checkout stays at the same commit, so `fetched_at` is the date the data was
really fetched, not the date of the last run.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CATALOG_DIR = DATA_DIR / "dbms_research"
REPO_URL = "https://github.com/samyama-ai/dbms_research.git"
PINNED_COMMIT = "5fff7f74508a52ac238f3bb608b8c8c872489fec"  # committed 2026-09-09


class CatalogError(RuntimeError):
    """The catalog checkout is not in the state a reproducible build needs."""


def git(*args: str, cwd: Path | None = None) -> str:
    """Run one git command and return what it printed."""
    result = subprocess.run(["git", *args], cwd=cwd, check=True,
                            capture_output=True, text=True)
    return result.stdout.strip()


def lock_path(root: Path) -> Path:
    """The lock file for the checkout at `root`: data/dbms_research -> data/dbms_research.lock.json."""
    return root.with_name(root.name + ".lock.json")


def read_lock(root: Path) -> dict | None:
    """The recorded fetch, or None when there is no readable lock file."""
    path = lock_path(root)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def count_problem_pages(root: Path) -> int:
    """Problem pages are topics/<topic>/<slug>.md. Each topic's README.md is an index, not a problem."""
    return sum(1 for page in (root / "topics").glob("*/*.md") if page.name != "README.md")


def same_repo(a: str, b: str) -> bool:
    """True when two git URLs or paths name the same repo (ignoring a trailing / or .git)."""
    def norm(url: str) -> str:
        return url.rstrip("/").removesuffix(".git")
    return norm(a) == norm(b)


def origin_url(root: Path) -> str:
    """The clone's origin URL; a clone without an origin remote is refused."""
    try:
        return git("remote", "get-url", "origin", cwd=root)
    except subprocess.CalledProcessError as error:
        raise CatalogError(f"{root} has no 'origin' remote; re-clone it with python -m etl.download_data") from error


def resolve_commit(root: Path, commit: str) -> str | None:
    """The full 40-hex SHA that `commit` (full or short SHA, tag) names in the clone, or None."""
    if not commit or commit.startswith("-"):
        raise CatalogError(f"{commit!r} is not a commit")   # never pass an option to git
    result = subprocess.run(["git", "rev-parse", "--verify", "--quiet", f"{commit}^{{commit}}"],
                            check=False, cwd=root, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def check_catalog(root: Path = CATALOG_DIR, commit: str = PINNED_COMMIT,
                  repo_url: str = REPO_URL) -> str:
    """Raise CatalogError unless `root` is a clean clone of `repo_url` at `commit`. Return the full SHA."""
    if not (root / ".git").exists():
        raise CatalogError(f"{root} is not a git clone; run: python -m etl.download_data")
    remote = origin_url(root)
    if not same_repo(remote, repo_url):
        raise CatalogError(f"{root} is a clone of {remote}, not {repo_url}")
    if git("status", "--porcelain", cwd=root):
        raise CatalogError(f"{root} has local changes; a build from it would not be reproducible")
    head = git("rev-parse", "HEAD", cwd=root)
    wanted = resolve_commit(root, commit)
    if head != wanted:
        raise CatalogError(f"{root} is at {head[:8]}, not the pinned {commit[:8]}; "
                           "run: python -m etl.download_data")
    return head


def download(root: Path = CATALOG_DIR, commit: str = PINNED_COMMIT,
             repo_url: str = REPO_URL) -> dict:
    """Clone or update the catalog at `root`, check out `commit`, write the lock file. Return the lock."""
    root.parent.mkdir(parents=True, exist_ok=True)

    # 1. Get a clone.
    if root.exists() and not (root / ".git").exists():
        raise CatalogError(f"{root} exists but is not a git clone; move it away first")
    if not root.exists():
        git("clone", "--quiet", repo_url, str(root))

    # 2. Refuse to touch a clone of another repo or one with local edits, before checking anything out.
    remote = origin_url(root)
    if not same_repo(remote, repo_url):
        raise CatalogError(f"{root} is a clone of {remote}, not {repo_url}")
    if git("status", "--porcelain", cwd=root):
        raise CatalogError(f"{root} has local changes; commit or discard them first")

    # 3. Find the commit: locally, then after fetching branches and tags, then by
    #    fetching the commit itself (it may be unreachable from any advertised ref).
    sha = resolve_commit(root, commit)
    if sha is None:
        git("fetch", "--quiet", "origin", cwd=root)
        sha = resolve_commit(root, commit)
    if sha is None:
        subprocess.run(["git", "fetch", "--quiet", "origin", commit], check=False, cwd=root, capture_output=True, text=True)
        sha = resolve_commit(root, commit)
    if sha is None:
        raise CatalogError(f"commit {commit!r} was not found in {repo_url}")
    git("checkout", "--quiet", "--detach", sha, cwd=root)
    head = check_catalog(root, sha, repo_url)

    # 4. Record the fetch. Keep an existing lock for the same commit and repo, so
    #    fetched_at stays the real date.
    lock = read_lock(root)
    if not lock or lock.get("commit") != head or not same_repo(lock.get("repo", ""), repo_url):
        lock = {
            "repo": repo_url,
            "commit": head,
            "commit_date": git("show", "-s", "--format=%cI", head, cwd=root),
            "fetched_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "problem_files": count_problem_pages(root),
        }
        lock_path(root).write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    return lock


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--commit", default=PINNED_COMMIT,
                        help="commit to check out (default: PINNED_COMMIT)")
    args = parser.parse_args(argv)
    try:
        lock = download(commit=args.commit)
    except FileNotFoundError:
        parser.exit(1, "[download] error: git is not installed or not on PATH\n")
    except (CatalogError, subprocess.CalledProcessError) as error:
        detail = getattr(error, "stderr", "") or ""
        parser.exit(1, f"[download] error: {error} {detail}".rstrip() + "\n")
    print(f"[download] {lock['repo']} @ {lock['commit'][:12]} "
          f"(committed {lock['commit_date'][:10]}, fetched {lock['fetched_at'][:10]}, "
          f"{lock['problem_files']} problem pages) -> {CATALOG_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
