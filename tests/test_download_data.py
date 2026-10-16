"""Tests for etl/download_data.py, run against a small fake catalog repo (no network)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from etl.download_data import (
    CatalogError,
    check_catalog,
    count_problem_pages,
    download,
    lock_path,
    main,
)

GIT_ID = ["-c", "user.name=Test", "-c", "user.email=test@example.com"]


def run(*args: str, cwd: Path) -> str:
    return subprocess.run(["git", *GIT_ID, *args], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout.strip()


def commit_all(repo: Path, message: str) -> str:
    run("add", "-A", cwd=repo)
    run("commit", "--quiet", "-m", message, cwd=repo)
    return run("rev-parse", "HEAD", cwd=repo)


@pytest.fixture
def upstream(tmp_path: Path) -> tuple[Path, str]:
    """A fake catalog: one topic with an index README and two problem pages."""
    repo = tmp_path / "upstream"
    (repo / "topics" / "01-relational-theory").mkdir(parents=True)
    run("init", "--quiet", cwd=repo)
    (repo / "topics" / "01-relational-theory" / "README.md").write_text("# index\n")
    (repo / "topics" / "01-relational-theory" / "a.md").write_text("# A\n")
    (repo / "topics" / "01-relational-theory" / "b.md").write_text("# B\n")
    return repo, commit_all(repo, "first")


def test_fresh_download_writes_lock(tmp_path, upstream):
    repo, sha = upstream
    root = tmp_path / "data" / "dbms_research"
    lock = download(root, sha, str(repo))
    assert lock["commit"] == sha
    assert lock["problem_files"] == 2            # README.md is not a problem page
    assert lock["repo"] == str(repo)
    assert json.loads(lock_path(root).read_text()) == lock
    assert check_catalog(root, sha, str(repo)) == sha


def test_rerun_keeps_the_fetch_date(tmp_path, upstream):
    repo, sha = upstream
    root = tmp_path / "data" / "dbms_research"
    download(root, sha, str(repo))
    old = json.loads(lock_path(root).read_text())
    old["fetched_at"] = "2026-10-14T07:32:29+00:00"     # pretend it was fetched earlier
    lock_path(root).write_text(json.dumps(old))
    assert download(root, sha, str(repo))["fetched_at"] == "2026-10-14T07:32:29+00:00"


def test_new_commit_fetches_and_rewrites_lock(tmp_path, upstream):
    repo, first = upstream
    root = tmp_path / "data" / "dbms_research"
    download(root, first, str(repo))
    (repo / "topics" / "01-relational-theory" / "c.md").write_text("# C\n")
    second = commit_all(repo, "second")              # not in the clone yet: needs a fetch
    lock = download(root, second, str(repo))
    assert lock["commit"] == second
    assert lock["problem_files"] == 3


def test_local_changes_are_refused(tmp_path, upstream):
    repo, sha = upstream
    root = tmp_path / "data" / "dbms_research"
    download(root, sha, str(repo))
    (root / "topics" / "01-relational-theory" / "a.md").write_text("edited\n")
    with pytest.raises(CatalogError, match="local changes"):
        download(root, sha, str(repo))
    with pytest.raises(CatalogError, match="local changes"):
        check_catalog(root, sha, str(repo))


def test_clone_of_another_repo_is_refused(tmp_path, upstream):
    repo, sha = upstream
    root = tmp_path / "data" / "dbms_research"
    download(root, sha, str(repo))
    with pytest.raises(CatalogError, match="is a clone of"):
        download(root, sha, "https://github.com/someone/else.git")


def test_folder_that_is_not_a_clone_is_refused(tmp_path, upstream):
    repo, sha = upstream
    root = tmp_path / "data" / "dbms_research"
    root.mkdir(parents=True)
    with pytest.raises(CatalogError, match="not a git clone"):
        download(root, sha, str(repo))


def test_wrong_commit_is_reported(tmp_path, upstream):
    repo, first = upstream
    root = tmp_path / "data" / "dbms_research"
    download(root, first, str(repo))
    (repo / "topics" / "01-relational-theory" / "c.md").write_text("# C\n")
    second = commit_all(repo, "second")
    with pytest.raises(CatalogError, match="not the pinned"):
        check_catalog(root, second, str(repo))


def test_count_skips_topic_readmes(tmp_path):
    (tmp_path / "topics" / "01-x").mkdir(parents=True)
    (tmp_path / "topics" / "01-x" / "README.md").write_text("")
    (tmp_path / "topics" / "01-x" / "p.md").write_text("")
    (tmp_path / "topics" / "README.md").write_text("")  # not inside a topic folder: not counted either
    assert count_problem_pages(tmp_path) == 1


def test_short_sha_is_resolved_to_the_full_commit(tmp_path, upstream):
    repo, sha = upstream
    root = tmp_path / "data" / "dbms_research"
    lock = download(root, sha[:12], str(repo))
    assert lock["commit"] == sha
    assert check_catalog(root, sha[:8], str(repo)) == sha


def test_option_like_commit_is_refused(tmp_path, upstream):
    repo, sha = upstream
    root = tmp_path / "data" / "dbms_research"
    download(root, sha, str(repo))
    with pytest.raises(CatalogError, match="is not a commit"):
        download(root, "--output=/tmp/x", str(repo))


def test_unknown_commit_gives_a_clear_error(tmp_path, upstream):
    repo, _ = upstream
    root = tmp_path / "data" / "dbms_research"
    with pytest.raises(CatalogError, match="was not found"):
        download(root, "0" * 40, str(repo))


def test_lock_from_another_repo_is_not_reused(tmp_path, upstream):
    repo, sha = upstream
    root = tmp_path / "data" / "dbms_research"
    download(root, sha, str(repo))
    old = json.loads(lock_path(root).read_text())
    old.update(repo="https://example.com/other.git", fetched_at="2000-01-01T00:00:00+00:00")
    lock_path(root).write_text(json.dumps(old))
    lock = download(root, sha, str(repo))
    assert lock["repo"] == str(repo)
    assert lock["fetched_at"] != "2000-01-01T00:00:00+00:00"


def test_clone_without_origin_is_refused(tmp_path, upstream):
    repo, sha = upstream
    root = tmp_path / "data" / "dbms_research"
    download(root, sha, str(repo))
    run("remote", "remove", "origin", cwd=root)
    with pytest.raises(CatalogError, match="no 'origin' remote"):
        download(root, sha, str(repo))


def test_main_exits_nonzero_with_a_readable_message(tmp_path, monkeypatch, capsys):
    import etl.download_data as dd
    folder = tmp_path / "data" / "dbms_research"
    folder.mkdir(parents=True)                       # exists but is not a clone
    monkeypatch.setattr(dd.download, "__defaults__", (folder, dd.PINNED_COMMIT, dd.REPO_URL))
    with pytest.raises(SystemExit) as stop:
        main([])
    assert stop.value.code == 1
    assert "[download] error:" in capsys.readouterr().err
