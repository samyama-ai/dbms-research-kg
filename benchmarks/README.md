# Benchmarks

The 48 questions of [scope.md](scope.md), each answered twice: as Cypher on the loaded
graph, and again from the raw catalog pages.

| File | |
|---|---|
| [`scope_questions.cypher`](scope_questions.cypher) | Every question as Cypher, ready to paste into Samyama Insight or run with the client |
| [`reference.py`](reference.py) | Every question answered again from the raw pages with plain regexes, and the verdict of the comparison |
| [`run.py`](run.py) | Runs and times the Cypher, joins each answer to its verdict, and writes the `.md` |
| [`scope_questions.md`](scope_questions.md) | The result: each question with its answer, rows, time and verdict |
| [`scope.md`](scope.md) | The 48 questions the graph is built to answer, in eight groups |
| [`quality-report.md`](quality-report.md), [`audit-report.md`](audit-report.md) | The generated reports of `python -m etl.quality` (18 criteria) and `python -m etl.audit` (22 items) |

```bash
python -m benchmarks.reference                         # verdicts only; needs data/ and build/, no engine
python -m benchmarks.run --url http://127.0.0.1:8094   # the Cypher on a loaded graph, then the verdicts
```

`run` exits non-zero if any query errors, if any verdict is WRONG, or if the questions that return
no rows are not exactly the expected ones: Q26 and Q44 (documented limits: no DBLP or ORCID lookup;
each future direction belongs to one problem) and Q46-Q48 (questions the graph must refuse). Q39
(similar problems by meaning) needs vector search and has no Cypher here.

## Why every question has a reference

A query that runs has not been shown to be right. `reference.py` re-reads the catalog's Markdown
with simple regexes, not through the graph parser, so a mistake in the parser is not copied into
the check. Each question gets one verdict:

- **correct**: the answer equals the value read from the raw pages;
- **consistent**: for computed links, which no page states, the answer agrees with the graph's own
  evidence;
- **limited**: a documented partial answer (for example "no DBLP lookup"), and the limit holds;
- **refused**: a question the graph must refuse, and it returns nothing;
- **WRONG**: anything else.

## Adding a question

1. Add it to [`scope.md`](scope.md) with the next number.
2. Add its answer to `etl/questions.py` and its raw-page check to `reference.py`, written from the
   question and the page, not from the Cypher.
3. Add a block `// Q<n> · <question>` and its Cypher to `scope_questions.cypher`.
4. Run `pytest`, then `python -m benchmarks.run` on a loaded graph.

## Results

Full graph, 20,211 nodes and 53,721 edges, Samyama 1.11.0, Linux x86_64, measured 2026-10-16.
**17 correct, 8 consistent, 20 limited, 3 refused, 0 wrong.** The 47 queries return in 1 to 57 ms
each, half in 3 ms or less. Every row, time and answer is in [`scope_questions.md`](scope_questions.md).

One machine, one run of the suite. Treat the times as an order of magnitude, not a benchmark result.
See [`docs/engine-notes.md`](../docs/engine-notes.md) for load times.
