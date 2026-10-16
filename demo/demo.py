"""Narrated terminal demo: the DBMS Research knowledge graph on Samyama.

    python -m demo.demo                                   # the server on http://127.0.0.1:8094
    python -m demo.demo --url http://127.0.0.1:8092
    python -m demo.demo --no-pause                        # no pacing, for a log or a test
    python -m demo.demo --long                            # long form: one tall report, for the GIF
    python -m demo.demo --write-cypher                    # write the ten queries to demo/queries.cypher

Ten questions a database researcher starts from, in one walk: how open the field is, which topics
are most open, the papers the problems share, the labs and systems named on them, which lower
bounds are conditional, where the gap is closed, which problems are close to one problem, how the
concepts nest, and a question the graph must refuse.

EVERY NUMBER HERE IS READ FROM THE GRAPH AT RUN TIME. Nothing is typed in, so the demo cannot claim
something the graph no longer contains. Each step is tagged with what its answer rests on: text
parsed from the catalog page, one of our fixed rules (a reviewed list or keyword rule), a computed
link, or nothing (the graph holds no such data), so a viewer can tell a stated fact from a
classification we made.

The demo needs a server that holds the graph. Load the snapshot shared inside the team, or build it:

    docker run -d --name samyama-dbms -p 127.0.0.1:8094:8080 ghcr.io/samyama-ai/samyama-graph:latest
    python -m etl.snapshot import --url http://127.0.0.1:8094     # or: python -m etl.loader --url ... --load
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import click
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

DEFAULT_URL = "http://127.0.0.1:8094"
GRAPH = "default"                       # engine 1.11.0 serves exactly one graph, named "default"
CYPHER_PATH = Path(__file__).resolve().parent / "queries.cypher"
EXAMPLE_PROBLEM = "01-relational-theory/acyclic-join-dependencies"

BASIS = {
    "parsed": ("PARSED FROM THE PAGE", "green", "read as written from the problem page"),
    "rule": ("OUR FIXED RULE", "magenta", "a reviewed list or keyword rule: etl/source_entities.py, etl/classify.py"),
    "computed": ("COMPUTED LINK", "yellow", "RELATED_TO: problems that cite the same papers, with a score"),
    "none": ("NO SUCH DATA", "red", "the graph must return nothing"),
}
LONG_TAG = {k: f"[{colour}]{label.lower()}[/{colour}]" for k, (label, colour, _) in BASIS.items()}

# (title, what to say before it, rests on, rows to show, cypher)
STORY = [
    ("How open is the field?",
     "1,053 problems, one catalog page each. Their status, as the page header states it.", "parsed", 4,
     "MATCH (p:Problem) RETURN p.status AS status, count(p) AS problems ORDER BY problems DESC"),
    ("Which topics have the most open problems?",
     "The 35 topics of TAXONOMY.md; every problem sits in exactly one.", "parsed", 5,
     ("MATCH (p:Problem {status: 'open'})-[:IN_TOPIC]->(t:Topic) "
     "RETURN t.name AS topic, count(p) AS open_problems ORDER BY open_problems DESC, topic LIMIT 5")),
    ("Which papers are cited by the most problems?",
     "One node per paper: citations by DOI, arXiv id, DBLP key or title and year are merged.", "parsed", 5,
     ("MATCH (p:Problem)-[:CITES]->(x:Paper) "
     "RETURN x.title AS paper, x.year AS year, count(p) AS problems ORDER BY problems DESC, paper LIMIT 5")),
    ("Which labs are named on the most open problems?",
     "Labs named in 'Current Research', matched against a checked list of 83 institutions.", "rule", 6,
     ("MATCH (i:Institution)-[:ACTIVE_ON]->(p:Problem {status: 'open'}) "
     "RETURN i.name AS institution, i.kind AS kind, count(p) AS open_problems "
     "ORDER BY open_problems DESC, institution LIMIT 6")),
    ("Which systems are state of the art for the most problems?",
     "Names written in bold in 'State of the Art', labelled by their Theory/Systems bullet.", "rule", 6,
     ("MATCH (p:Problem)-[:STATE_OF_ART]->(s:System) "
     "RETURN s.name AS system, s.family AS family, count(p) AS problems ORDER BY problems DESC, system LIMIT 6")),
    ("Which lower bounds rest on a fine-grained hypothesis such as SETH?",
     "'Lower Bound' text matched to computation models; conditional hardness is its own class.", "rule", 5,
     ("MATCH (p:Problem)-[:HAS_BOUND]->(b:Bound {direction: 'lower'})-[:IN_MODEL]->"
     "(m:ComputationModel {class: 'fine-grained'})-[:CLASSIFIED_AS]->(:TaxonomyTerm) "
     "MATCH (p)-[:IN_TOPIC]->(t:Topic) "
     "RETURN t.name AS topic, count(DISTINCT p) AS problems ORDER BY problems DESC, topic LIMIT 5")),
    ("Where is the gap between the bounds closed, and where is it still open?",
     "'The Gap' read for its verdict: the page's own bold word first, otherwise a keyword rule.", "rule", 5,
     ("MATCH (p:Problem)-[:HAS_GAP]->(g:Gap) "
     "RETURN g.verdict AS gap_verdict, count(p) AS problems, "
     "sum(CASE WHEN g.verdict_method = 'stated' THEN 1 ELSE 0 END) AS stated_by_the_page "
     "ORDER BY problems DESC")),
    ("Which problems are closest to acyclic join dependency recognition?",
     "Not stated anywhere: computed from shared cited papers and concepts, with a Jaccard score.", "computed", 5,
     (f"MATCH (a:Problem {{id: '{EXAMPLE_PROBLEM}'}})-[r:RELATED_TO]-(b:Problem) "
     "RETURN b.title AS related_problem, r.shared_papers AS shared_papers, r.score AS score "
     "ORDER BY score DESC, related_problem LIMIT 5")),
    ("How do the width measures nest?",
     "Concepts from 'Mathematical Foundations' with a reviewed broader-narrower hierarchy.", "rule", 5,
     ("MATCH (a:Concept)-[:GENERALIZES]->(b:Concept) WHERE a.name CONTAINS 'width' OR b.name CONTAINS 'width' "
     "OR b.name = 'acyclicity' RETURN a.name AS broader, b.name AS narrower ORDER BY broader, narrower")),
    ("How much funding has each problem received?",
     "The catalog says nothing about funding, so the graph says nothing.", "none", 3,
     "MATCH (p:Problem) WHERE p.funding IS NOT NULL RETURN p.title AS problem, p.funding AS funding LIMIT 3"),
]

TAKEAWAY = ("Status, topics, shared papers, named labs and systems, conditional bounds, gap verdicts,\n"
            "related problems and the concept hierarchy, all answered as graph traversals over\n"
            "one pinned catalog commit. Every row leads back to the page it was read from.")


def cell(value, column: str = "") -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        text = f"{value:,.3f}".rstrip("0")
        return text + "0" if text.endswith(".") else text
    if isinstance(value, int):
        return str(value) if column.endswith("year") else f"{value:,}"
    if isinstance(value, list):
        return "; ".join(str(v) for v in value)
    text = str(value)
    return text if len(text) <= 70 else text[:67] + "…"


def long_pause(seconds: float, enabled: bool) -> None:
    """DEMO_PACE tunes the recording's cadence without an edit, as in the sibling KGs."""
    if enabled:
        time.sleep(seconds * float(os.environ.get("DEMO_PACE", "1.0")))


def count(client, graph_name: str, pattern: str) -> int:
    return client.query(f"MATCH {pattern} RETURN count(*)", graph_name).records[0][0]


def run_long(console: Console, client, graph_name: str, paced: bool) -> list[str]:
    """Long form, the layout of samyama-graph/case_studies/_lib/demo_lib.py: one tall report."""
    nodes = count(client, graph_name, "(n)")
    edges = count(client, graph_name, "()-[r]->()")
    problems = count(client, graph_name, "(n:Problem)")
    papers = count(client, graph_name, "(n:Paper)")
    systems = count(client, graph_name, "(n:System)") + count(client, graph_name, "(n:Algorithm)")
    commit = client.query("MATCH (d:DataSource) RETURN d.version", graph_name).records[0][0]

    console.print(Panel.fit(
        "[bold]Samyama · DBMS Research Knowledge Graph[/bold]\n"
        f"{problems:,} open problems · {papers:,} cited papers · {systems:,} named systems and algorithms · 35 topics\n"
        f"[dim]source: github.com/samyama-ai/dbms_research at {str(commit)[:8]}"
        " · no external lookups, no LLM extraction[/dim]",
        border_style="cyan"))
    long_pause(1.4, paced)

    console.print()
    console.rule("[bold cyan]1 · Graph loaded into Samyama")
    long_pause(0.5, paced)
    console.print(f"  [green]loaded[/green] [bold]{nodes:,}[/bold] nodes · [bold]{edges:,}[/bold] edges")
    long_pause(1.3, paced)

    wrong = []
    for index, (title, lead, basis, rows, statement) in enumerate(STORY, start=1):
        console.print()
        console.rule(f"[bold cyan]{index + 1} · {title}")
        long_pause(0.5, paced)
        console.print(f"  [dim]Q{index}.[/dim] [bold white]{title}[/bold white]  [dim]·[/dim] {LONG_TAG[basis]}")
        console.print(f"       [italic dim]{lead}[/italic dim]")
        console.print(f"  [dim]cypher>[/dim] [yellow]{escape(' '.join(statement.split()))}[/yellow]")

        began = time.perf_counter()
        result = client.query(statement, graph_name)
        took = 1000 * (time.perf_counter() - began)

        if result.records:
            table = Table(show_edge=False, pad_edge=False, box=None, header_style="bold magenta")
            for column in result.columns:
                table.add_column(str(column))
            for row in result.records[:rows]:
                table.add_row(*(cell(v, c) for v, c in zip(row, result.columns, strict=False)))
            console.print(table)
        more = len(result.records) - rows
        note = f" (showing {rows})" if more > 0 else ""
        console.print(f"  [green]→[/green] {len(result.records)} row(s){note} in [bold]{took:.1f} ms[/bold]"
                      + ("  [red]as it must: no such data[/red]" if basis == "none" else ""))
        long_pause(3.2, paced)
        if bool(result.records) == (basis == "none"):
            wrong.append(f"Q{index}")

    console.print()
    console.print(Panel.fit(f"[bold green]{TAKEAWAY}[/bold green]", border_style="green"))
    console.print("  [dim]Labs, systems, models, gap verdicts and the concept hierarchy are our classifications\n"
                  "  of the catalog's words; RELATED_TO is computed. Authors are kept as written.[/dim]")
    long_pause(1.6, paced)
    return wrong


def show(console: Console, client, graph_name: str, step: int, title: str, lead: str, basis: str,
         rows: int, statement: str, pause) -> bool:
    tag, colour, meaning = BASIS[basis]
    console.rule(f"[bold]{step}/{len(STORY)}  {title}[/bold]")
    console.print(lead)
    console.print(f"[{colour}]\\[{tag}][/{colour}] [dim]{meaning}[/dim]\n")
    console.print(statement + "\n", style="dim", highlight=False, markup=False)
    pause(1.5)

    began = time.perf_counter()
    result = client.query(statement, graph_name)
    took = 1000 * (time.perf_counter() - began)

    if result.records:
        table = Table(show_edge=False, header_style="bold")
        for column, sample in zip(result.columns, result.records[0], strict=False):
            numeric = isinstance(sample, (int, float)) and not isinstance(sample, bool)
            table.add_column(column, justify="right" if numeric else "left")
        for row in result.records[:rows]:
            table.add_row(*(cell(v, c) for v, c in zip(row, result.columns, strict=False)))
        console.print(table)
    more = len(result.records) - rows
    note = f"  and {more} more" if more > 0 else ""
    console.print(f"[dim]{len(result.records)} rows in {took:.0f} ms{note}[/dim]\n")
    pause(4.0)
    return bool(result.records) != (basis == "none")


def write_cypher(path: Path = CYPHER_PATH) -> Path:
    """The ten queries in full, in the order the demo runs them, ready to paste into Insight."""
    lines = ["// The ten queries of the demo, in the order it runs them.",
             "// Written by `python -m demo.demo --write-cypher`. Do not edit: edit STORY in demo/demo.py.", ""]
    for step, (title, lead, basis, _rows, statement) in enumerate(STORY, start=1):
        lines += [f"// {step}. {title}  (rests on: {basis})", f"// {lead}", statement + ";", ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def connect(url: str):
    from samyama import SamyamaClient
    client = SamyamaClient.connect(url)
    try:
        nodes = client.query("MATCH (n) RETURN count(n)", GRAPH).records[0][0]
    except Exception as exc:
        raise click.ClickException(
            f"cannot query {url} ({exc}). Start a server and load the graph:\n"
            "  docker run -d --name samyama-dbms -p 127.0.0.1:8094:8080 ghcr.io/samyama-ai/samyama-graph:latest\n"
            "  python -m etl.snapshot import --url http://127.0.0.1:8094") from exc
    if not nodes:
        raise click.ClickException(f"{url} holds an empty graph: python -m etl.snapshot import --url {url}")
    return client


@click.command()
@click.option("--url", default=DEFAULT_URL, show_default=True, help="Samyama server holding the graph.")
@click.option("--graph", "graph_name", default=GRAPH, show_default=True, help="Graph to query.")
@click.option("--no-pause", is_flag=True, help="Do not pace the output.")
@click.option("--long", "long_form", is_flag=True, help="Long form: one tall report, in the case-study layout.")
@click.option("--write-cypher", "only_write", is_flag=True,
              help="Write the ten queries to demo/queries.cypher and exit.")
def main(url, graph_name, no_pause, long_form, only_write):
    if only_write:
        click.echo(f"wrote {write_cypher()}")
        return
    console = Console(width=100)
    client = connect(url)

    if long_form:
        wrong = run_long(console, client, graph_name, not no_pause)
        if wrong:
            console.print(f"[red]these steps did not return what they must: {', '.join(wrong)}[/red]")
            sys.exit(1)
        return

    def pause(seconds: float) -> None:
        if not no_pause:
            time.sleep(seconds)

    console.print(Panel.fit(
        "[bold]DBMS Research Knowledge Graph[/bold]\n"
        "1,053 open problems in database systems research, with the papers, people, labs, systems,\n"
        "bounds and gaps around them, from one pinned catalog commit.",
        border_style="cyan"))
    console.print(f"[dim]connected to {url}, graph {graph_name}[/dim]\n")
    pause(2.0)
    wrong = [f"Q{step}" for step, (title, lead, basis, rows, statement) in enumerate(STORY, start=1)
             if not show(console, client, graph_name, step, title, lead, basis, rows, statement, pause)]

    console.print(Panel.fit(
        "[green]Parsed from the page[/green]  status, topics, papers, bounds: as the catalog writes them\n"
        "[magenta]Our fixed rule[/magenta]        labs, systems, models, gap verdicts, concepts:"
        " reviewed lists and rules\n"
        "[yellow]Computed link[/yellow]         RELATED_TO: shared cited papers and concepts, with a score\n"
        "[red]No such data[/red]          funding, global citation counts: the graph refuses\n\n"
        "Source: github.com/samyama-ai/dbms_research (one commit, no external lookups, no LLM extraction).",
        title="What you just saw", border_style="cyan"))
    pause(5.0)

    if wrong:
        console.print(f"[red]these steps did not return what they must: {', '.join(wrong)}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
