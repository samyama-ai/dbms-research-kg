# Demo

![DBMS Research KG demo](dbms-research-kg.gif)

Ten queries, one story: what is open in database systems research, why, and who is working on it.
Each answer is tagged with what it rests on, because some values are the catalog's words and some
are our rules over them.

| # | Question | Rests on |
|---:|---|---|
| 1 | How open is the field? | parsed from the page |
| 2 | Which topics have the most open problems? | parsed from the page |
| 3 | Which papers are cited by the most problems? | parsed from the page |
| 4 | Which labs are named on the most open problems? | our fixed rule |
| 5 | Which systems are state of the art for the most problems? | our fixed rule |
| 6 | Which lower bounds rest on a fine-grained hypothesis such as SETH? | our fixed rule |
| 7 | Where is the gap between the bounds closed, and where is it still open? | our fixed rule |
| 8 | Which problems are closest to acyclic join dependency recognition? | computed link |
| 9 | How do the width measures nest? | our fixed rule |
| 10 | How much funding has each problem received? | no such data: the graph returns nothing |

**Parsed from the page** is the catalog's own words. **Our fixed rule** is a reviewed list or a
keyword rule of this project (labs, systems, models, gap verdicts, concepts). A **computed link** is
RELATED_TO, from shared papers and concepts. **No such data** is a question the graph must refuse.

The ten queries in full are in [`queries.cypher`](queries.cypher), written from the demo itself by
`python -m demo.demo --write-cypher`; edit `STORY` in `demo.py`, not the file.

## Run it

With a server that holds the graph (`python -m etl.loader ... --load` or
`python -m etl.snapshot import`):

```bash
python -m demo.demo --url http://127.0.0.1:8094            # paced, for a live walk-through
python -m demo.demo --long --url http://127.0.0.1:8094     # one tall report, the case-study layout
python -m demo.demo --no-pause --url http://127.0.0.1:8094 # no pacing
python -m demo.demo --write-cypher                          # the ten queries -> demo/queries.cypher
```

Every number is read from the graph at run time, including the counts on the title card.

## The recording

Long form: the whole report on one tall screen, with nothing scrolling off. The layout and the
recording settings are those of the case studies in `samyama-graph/case_studies`, as in the other
Samyama KGs.

| File | |
|---|---|
| `dbms-research-kg.gif` | the GIF shown in the README |
| `dbms-research-kg.cast` | the asciinema recording the GIF was rendered from |
| `record.sh` | records and renders both |

The finished report is held for 14 seconds before the GIF starts again. Recorded on 2026-10-16
against the full graph, 20,211 nodes and 53,721 edges, on a Samyama 1.11.0 server.

### Record it again

Needs `asciinema` (`pip install asciinema==2.4.0`) and `agg` (github.com/asciinema/agg), and a
server that holds the graph:

```bash
demo/record.sh                                    # http://127.0.0.1:8094, graph default
demo/record.sh http://127.0.0.1:8095 default      # another server
AGG=/path/to/agg demo/record.sh                   # agg not on PATH
GIF_HOLD=20 demo/record.sh                        # a longer hold at the end
```

The height of the recording is measured from the demo's own output, so adding a query cannot push
the first one off the top. Record it again whenever the graph changes.
