"""Export the built graph as a `.sgsnap`, and load it back without running the ETL.

    python -m etl.snapshot export --url http://127.0.0.1:8094   # after loading the graph into that server
    python -m etl.snapshot import --url http://127.0.0.1:8092   # into a FRESH server
    python -m etl.snapshot import --url ... --file other.sgsnap --manifest other.json

WHY. Building the graph needs the catalog checkout (data/, not committed) and a few minutes.
A snapshot is the built graph itself: anyone with a Samyama server can have it in seconds.

A `.sgsnap` is serialised ENGINE STATE, not a build. `snapshots/manifest.json` records the git commit
that built it, the engine version, the counts per label and relationship, and a SHA-256, so a stale
snapshot is visible. Re-export when the code or data changes. The manifest names the file it
describes, and `import` refuses a file/manifest pair that does not match.

THE TRAP (measured by interconnect-ip-kg, 2026-09-21; copied from ai-research-kg): import APPENDS, silently. A second import
into the same server doubles every node and edge, with no error. So `import`:
  - refuses a graph that is not empty (checked by QUERY, not by the status counters), and
  - counts again afterwards and fails unless every count equals the manifest.
This engine has no transaction to roll back and `DETACH DELETE` is not a full reset
(observed on the AI Research KG), so a failed import leaves the server half-loaded: the message says
to recreate the container, which is the only clean recovery.

Engine: samyama-graph 1.11.0, which serves exactly one graph named 'default'.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
import urllib.request
import uuid
from pathlib import Path

import click

from etl.download_data import PINNED_COMMIT

ROOT = Path(__file__).resolve().parent.parent
SNAP_DIR = ROOT / "snapshots"
SNAP_FILE = SNAP_DIR / "dbms-research-kg.sgsnap"
MANIFEST = SNAP_DIR / "manifest.json"
GRAPH = "default"
COUNT_KEYS = ("nodes", "edges", "labels", "relationships")


def _post(url: str, body: bytes = b"", content_type: str | None = None, timeout: int = 600) -> bytes:
    req = urllib.request.Request(url, data=body, method="POST")
    if content_type:
        req.add_header("Content-Type", content_type)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read())


def counts(url: str) -> dict:
    """What the graph holds, asked of the graph by query, never of /api/status.

    Labels are counted one query per label, over every label the graph reports, so a node with
    several labels is counted under each of them (and the per-label sum may exceed `nodes`).
    """
    from samyama import SamyamaClient

    c = SamyamaClient.connect(url)
    one = lambda q: c.query(q, GRAPH).records[0][0]
    rows = lambda q: c.query(q, GRAPH).records     
    out = {"nodes": one("MATCH (n) RETURN count(n)"), "edges": one("MATCH ()-[r]->() RETURN count(r)")}
    labels = sorted({lab for (labs,) in rows("MATCH (n) RETURN DISTINCT labels(n)") for lab in labs})
    types = sorted(t for (t,) in rows("MATCH ()-[r]->() RETURN DISTINCT type(r)"))
    out["labels"] = {lab: one(f"MATCH (n:{_ident(lab)}) RETURN count(n)") for lab in labels}
    out["relationships"] = {t: one(f"MATCH ()-[r:{_ident(t)}]->() RETURN count(r)") for t in types}
    return out


def _ident(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise click.ClickException(f"unexpected label or type name in the graph: {name!r}")
    return name


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _commit() -> str:
    """The repo commit the export was made from, '-dirty' when tracked files differ; 'unknown' if git fails."""
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no", "--", ".", ":!snapshots"],
                               cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return sha + ("-dirty" if dirty else "")


def _load_manifest(path: Path) -> dict:
    if not path.exists():
        raise click.ClickException(f"no manifest at {path}: run `python -m etl.snapshot export` first, or pass --manifest")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise click.ClickException(f"{path} is not valid JSON: {error}") from error
    missing = [k for k in ("file", "sha256", *COUNT_KEYS) if k not in manifest]
    if missing:
        raise click.ClickException(f"{path} lacks {', '.join(missing)}")
    return manifest


@click.group()
def cli() -> None:
    pass


@cli.command("export")
@click.option("--url", required=True)
def export_cmd(url: str) -> None:
    url = url.rstrip("/")
    before = counts(url)
    if not before["nodes"]:
        raise click.ClickException("the graph is empty: load it first (python -m etl.loader --url ...)")
    SNAP_DIR.mkdir(exist_ok=True)
    SNAP_FILE.write_bytes(_post(url + "/api/snapshot/export"))
    after = counts(url)
    if after != before:   # the graph changed while the file was written: the counts would not describe the file
        raise click.ClickException("the graph changed during the export; re-run when nothing else is writing to it")
    manifest = {
        "file": SNAP_FILE.name, "bytes": SNAP_FILE.stat().st_size, "sha256": sha256(SNAP_FILE),
        "created": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "commit": _commit(), "engine_version": _get(url + "/api/status").get("version"),
        "graph": GRAPH, "catalog": "github.com/samyama-ai/dbms_research", "catalog_commit": PINNED_COMMIT,
        **after,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    click.echo(f"[snapshot] wrote {SNAP_FILE.relative_to(ROOT)} ({manifest['bytes'] / 1e6:.1f} MB): "
               f"{after['nodes']:,} nodes, {after['edges']:,} edges, engine {manifest['engine_version']}")
    if manifest["commit"].endswith("-dirty") or manifest["commit"] == "unknown":
        click.echo(f"[snapshot] warning: repo commit is {manifest['commit']}; commit and re-export before sharing")


@cli.command("import")
@click.option("--url", required=True)
@click.option("--file", "path", type=click.Path(exists=True, path_type=Path), default=SNAP_FILE, show_default=True)
@click.option("--manifest", "manifest_path", type=click.Path(path_type=Path), default=MANIFEST, show_default=True,
              help="The manifest that describes --file.")
def import_cmd(url: str, path: Path, manifest_path: Path) -> None:
    url = url.rstrip("/")
    manifest = _load_manifest(manifest_path)
    if manifest["file"] != path.name:
        raise click.ClickException(f"{manifest_path.name} describes {manifest['file']!r}, not {path.name!r}; pass the matching --manifest")
    if sha256(path) != manifest["sha256"]:
        raise click.ClickException(f"the SHA-256 of {path.name} does not match {manifest_path.name}")
    have = counts(url)["nodes"]
    if have:
        raise click.ClickException(f"the graph already holds {have:,} nodes. Import APPENDS silently and would "
                                   "duplicate everything: use a fresh server container.")
    boundary = uuid.uuid4().hex
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", path.name)      # header-safe: no quotes, CR or LF
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{safe_name}\"\r\n"
            "Content-Type: application/octet-stream\r\n\r\n").encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    try:
        _post(url + "/api/snapshot/import", body, f"multipart/form-data; boundary={boundary}")
        after = counts(url)
    except Exception as error:  # noqa: BLE001  any failure here can leave the server half-loaded
        sys.exit(f"[snapshot] import failed: {error}\n[snapshot] the server may be half-loaded; "
                 "recreate the container before trying again (DETACH DELETE is not a full reset)")
    diffs = {k: (after[k], manifest[k]) for k in COUNT_KEYS if after[k] != manifest[k]}
    if diffs:
        click.echo(json.dumps(diffs, indent=1))
        sys.exit("[snapshot] imported counts differ from the manifest (see above); the server is half-loaded, "
                 "recreate the container before trying again")
    click.echo(f"[snapshot] imported and verified: {after['nodes']:,} nodes, {after['edges']:,} edges")


if __name__ == "__main__":
    cli()
