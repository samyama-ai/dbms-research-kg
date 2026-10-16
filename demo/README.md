# Demo

`python -m demo.demo` walks ten questions through the loaded graph and tags each answer with what it
rests on: **parsed from the page**, **our fixed rule** (a reviewed list or keyword rule), a
**computed link** (`RELATED_TO`), or **no such data** (the graph must return nothing). Every number
is read from the graph when the demo runs.

```bash
python -m demo.demo --url http://127.0.0.1:8094          # paced, for a live walk-through
python -m demo.demo --long --no-pause --url ...           # one tall report, no pauses
python -m demo.demo --write-cypher                        # the ten queries -> demo/queries.cypher
AGG=/path/to/agg ./demo/record.sh http://127.0.0.1:8094   # re-record demo/dbms-research-kg.gif
```

`record.sh` needs `asciinema` (`pip install asciinema==2.4.0`) and `agg` 1.9
(github.com/asciinema/agg). The `.cast` recording is git-ignored; the GIF is committed and shown in
the README. Re-record the GIF whenever the graph changes.
