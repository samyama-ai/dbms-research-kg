"""Parse and validate the pinned DBMS Research catalog."""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

PINNED_COMMIT = "5fff7f74508a52ac238f3bb608b8c8c872489fec"
STATUSES = {"open", "partially-solved", "empirically-open", "solved-but-impractical"}
REQUIRED_METADATA = (
    "id", "title", "topic", "status", "first_added", "last_reviewed",
    "last_substantive_update", "stale_since", "provenance", "refs_checked",
)
REQUIRED_SECTIONS = (
    "problem_statement", "mathematical_foundations", "state_of_the_art",
    "upper_bound", "lower_bound", "gap", "current_research",
    "future_work", "key_references", "worked_example",
)
ALIASES = {
    "problem statement": "problem_statement",
    "mathematical foundations": "mathematical_foundations",
    "state of the art": "state_of_the_art",
    "upper bound": "upper_bound",
    "lower bound": "lower_bound",
    "the gap": "gap",
    "gap": "gap",
    "current research": "current_research",
    "future work": "future_work",
    "key references": "key_references",
    "worked example": "worked_example",
}
HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.+?)\s*$")


def scalar(value):
    value = value.strip()
    if not value:
        return ""
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if value.startswith(("'", '"')):
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return value[1:-1]
    return value


def frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return {}, text

    data = {}
    for line in lines[1:end]:
        if line.strip() and not line.lstrip().startswith("#") and ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = scalar(value)
    return data, "\n".join(lines[end + 1:])


def canonical_heading(value):
    value = re.sub(r"^\d+[a-z]?\s*[.)]?\s*", "", value.strip(), flags=re.I)
    value = re.sub(r"\s+", " ", value).lower()
    for alias, key in ALIASES.items():
        if value == alias or value.startswith(alias + " ") or value.startswith(alias + " ("):
            return key
    return None


def sections_from(body):
    lines = body.splitlines()
    headings = []
    for i, line in enumerate(lines):
        match = HEADING.match(line)
        if match:
            key = canonical_heading(match.group(2))
            if key:
                headings.append((i, len(match.group(1)), key))

    sections = {}
    for pos, (start, level, key) in enumerate(headings):
        end = len(lines)
        for next_start, next_level, _ in headings[pos + 1:]:
            if next_level <= level:
                end = next_start
                break
        sections.setdefault(key, "\n".join(lines[start + 1:end]).strip())
    return sections


def topic_title(folder):
    for name in ("README.md", "readme.md", "index.md", "INDEX.md"):
        path = folder / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            match = HEADING.match(line)
            if match:
                title = re.sub(r"^(topic|category)\s*:\s*", "", match.group(2).strip(), flags=re.I)
                return title or None
    return None


def list_items(text):
    result = []
    for line in text.splitlines():
        match = BULLET.match(line)
        if match and match.group(1).strip():
            result.append(match.group(1).strip())
    return result


def parse_problem(path, root):
    metadata, body = frontmatter(path.read_text(encoding="utf-8"))
    # README, index, and supporting files aren't problem records.
    if not all(metadata.get(key) for key in ("id", "title", "topic")):
        return None
    sections = sections_from(body)
    return {
        "id": str(metadata["id"]),
        "title": str(metadata["title"]),
        "topic_id": str(metadata["topic"]),
        "status": str(metadata.get("status", "")).strip(),
        "metadata": metadata,
        "sections": sections,
        "reference_entries": [
            line.strip() for line in sections.get("key_references", "").splitlines()
            if line.strip()
        ],
        "future_work_items": list_items(sections.get("future_work", "")),
        "source_path": path.relative_to(root).as_posix(),
    }


def git_commit(root):
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def build_catalog(root, expected_problems=1053, expected_topics=35, check_commit=True):
    root = root.resolve()
    errors, warnings = [], []
    topic_root = root / "topics"
    if not topic_root.is_dir():
        return {}, [f"Topics directory not found: {topic_root}"], warnings

    commit = git_commit(root)
    if check_commit and commit != PINNED_COMMIT:
        errors.append(f"Expected source commit {PINNED_COMMIT}; found {commit!r}")

    topic_dirs = {p.name: p for p in topic_root.iterdir() if p.is_dir()}
    if len(topic_dirs) != expected_topics:
        errors.append(f"Expected {expected_topics} topic directories; found {len(topic_dirs)}")

    problems = []
    for path in sorted(topic_root.rglob("*.md")):
        try:
            problem = parse_problem(path, root)
        except (OSError, UnicodeError) as exc:
            errors.append(f"Cannot read {path}: {exc}")
            continue
        if problem is not None:
            problems.append(problem)

    if len(problems) != expected_problems:
        errors.append(f"Expected {expected_problems} problem pages; found {len(problems)}")

    id_counts = Counter(p["id"] for p in problems)
    duplicates = sorted(k for k, count in id_counts.items() if count > 1)
    if duplicates:
        errors.append(f"Duplicate problem IDs: {duplicates[:20]}")

    for problem in problems:
        missing_meta = [key for key in REQUIRED_METADATA if key not in problem["metadata"]]
        if missing_meta:
            errors.append(f"{problem['id']}: missing metadata {missing_meta}")
        if problem["status"] not in STATUSES:
            errors.append(f"{problem['id']}: unexpected status {problem['status']!r}")
        missing_sections = [key for key in REQUIRED_SECTIONS if key not in problem["sections"]]
        if missing_sections:
            errors.append(f"{problem['id']}: missing sections {missing_sections}")
        if problem["topic_id"] not in topic_dirs:
            errors.append(f"{problem['id']}: topic directory not found: {problem['topic_id']}")

    topic_ids = sorted({p["topic_id"] for p in problems})
    topics = []
    for topic_id in topic_ids:
        title = topic_title(topic_dirs[topic_id]) if topic_id in topic_dirs else None
        if title is None:
            warnings.append(f"No topic title found in README/index for {topic_id}")
        topics.append({
            "id": topic_id,
            "title": title,
            "problem_count": sum(p["topic_id"] == topic_id for p in problems),
            "source_path": f"topics/{topic_id}",
        })

    status_counts = Counter(p["status"] for p in problems)
    catalog = {
        "schema_version": 1,
        "source": {
            "repository": "https://github.com/samyama-ai/dbms_research",
            "expected_commit": PINNED_COMMIT,
            "actual_commit": commit,
        },
        "counts": {
            "problem_pages": len(problems),
            "topics": len(topics),
            "statuses": dict(sorted(status_counts.items())),
            "reference_entries": sum(len(p["reference_entries"]) for p in problems),
            "future_work_items": sum(len(p["future_work_items"]) for p in problems),
            "pages_with_unverified_refs": sum(
                bool(p["metadata"].get("refs_unverified")) for p in problems
            ),
        },
        "topics": topics,
        "problems": problems,
    }
    # Carry retrieval and source-version dates forward from the reproducible lock
    # record. Never synthesize dates when that record is unavailable.
    lock_path = root.parent / "dbms_research.lock.json"
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        lock = {}
    if lock.get("commit") == commit:
        catalog["source"]["retrieved_at"] = str(lock.get("fetched_at", ""))[:10]
        catalog["source"]["source_date"] = str(lock.get("commit_date", ""))[:10]
    return catalog, errors, warnings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("data/dbms_research"))
    parser.add_argument("--output", type=Path, default=Path("build/source_catalog.json"))
    parser.add_argument("--expected-problems", type=int, default=1053)
    parser.add_argument("--expected-topics", type=int, default=35)
    parser.add_argument("--skip-commit-check", action="store_true")
    args = parser.parse_args()

    catalog, errors, warnings = build_catalog(
        args.source, args.expected_problems, args.expected_topics,
        check_commit=not args.skip_commit_check,
    )
    print("=== DBMS Research catalog validation ===")
    for warning in warnings:
        print("WARNING:", warning)
    if catalog:
        print(json.dumps(catalog.get("counts", {}), indent=2, ensure_ascii=False))
    if errors:
        print(f"\nFAILED: {len(errors)} validation error(s)")
        for error in errors[:100]:
            print("ERROR:", error)
        if len(errors) > 100:
            print(f"... plus {len(errors) - 100} more")
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"\nPASS: wrote {args.output} ({args.output.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
