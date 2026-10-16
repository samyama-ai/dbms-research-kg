# Data provenance

Where every part of this graph comes from, what terms it is offered under, and which parts are our
rules rather than the catalog's words.

## The short version

**One source, at one commit.** Everything is read from the
[DBMS Research catalog](https://github.com/samyama-ai/dbms_research) at commit
`5fff7f74508a52ac238f3bb608b8c8c872489fec` (2026-09-09): 35 topics and 1,053 problem pages. Nothing
is looked up elsewhere and nothing is generated.

| What | Nodes | Edges | How it is made |
|---|---:|---:|---|
| Read from the page | 18,378 | 29,835 | parsed from the page's header and sections: problems, topics, papers, authors, venues, bounds, gaps, current research, future work |
| Matched against our lists | 1,755 | 10,427 | names on a fixed list found in the page: concepts, institutions, algorithms, systems, computation models |
| Our classification | 77 codes | 3,720 | a rule over the page's words: problem type, technique family, model class, gap verdict, bound kind, the concept hierarchy |
| Computed | | 8,686 | RELATED_TO, from papers and concepts two problems share |
| The catalog itself | 1 | 1,053 | the DataSource node and FROM_SOURCE |

Every node carries `source_url`, the catalog file at the pinned commit, and `method`, which says
which of these rows made it:

```cypher
MATCH (n) RETURN n.method AS method, count(n) AS nodes ORDER BY nodes DESC
```

**The catalog's own pages are marked `synthesized`.** All 1,053 carry
`catalog_provenance: synthesized`, and the catalog describes itself as "a synthesized study aid, not
a primary source", written from established results and textbook theory and then put through
automated citation checks. The graph is faithful to the pages; it does not make them more true than
they are.

**Nothing downloaded is committed.** `data/` is git-ignored; the catalog is fetched at the pinned
commit by `python -m etl.download_data`.

## Terms of use

The catalog is **CC BY 4.0**, so the graph may be used for any purpose, including commercial use and
public display, with credit:

> Source: DBMS Research catalog, samyama-ai/dbms_research, CC BY 4.0.

The code in this repository is Apache 2.0. That licence does not cover the data. A snapshot of the
graph holds the catalog's text and falls under its terms.

This is a reading of the stated licence, made on 2026-10-14. It is not legal advice.

## The source

| | |
|---|---|
| Repository | `https://github.com/samyama-ai/dbms_research` |
| Commit | `5fff7f74508a52ac238f3bb608b8c8c872489fec`, dated 2026-09-09 |
| Pages | 1,053 problem pages in `topics/<nn>-<topic>/<slug>.md`; `TAXONOMY.md` for the 35 topics |
| Fetched | by `python -m etl.download_data`, which checks out the commit and refuses any other |
| Lock record | `data/dbms_research.lock.json`: the commit, its date, the fetch date and the page count. `retrieved_at` and `source_date` on every node come from it |

Each page follows the catalog's template, and the parser reads it section by section:

| Section | Becomes |
|---|---|
| header | Problem `status`, `first_added`, `last_reviewed`, `last_substantive_update`, `refs_checked`, `refs_unverified` |
| §1 Problem statement | Problem `statement`; the problem-type rule |
| §2 Mathematical foundations | RESTS_ON to Concept |
| §3 State of the art | STATE_OF_ART to Algorithm and System |
| §4, §5 Upper and lower bounds | Bound, IN_MODEL to ComputationModel |
| §6 The gap | Gap with its verdict |
| §7 Current research | ResearchDirection; ACTIVE_ON from Person and Institution; AFFILIATED_WITH |
| §8 Future work | FutureDirection |
| §9 Key references | Paper, CITES with its role, AUTHORED_BY, APPEARED_AT |
| §10 Worked example | Problem `worked_example` |

## Our rules over the catalog's words

These are ours, not the catalog's. Each is in code that a reviewer can read, and each assignment
records which rule made it.

| Rule | Where | Records |
|---|---|---|
| Concept list (90) and its hierarchy (31 pairs) | `CONCEPTS`, `CONCEPT_HIERARCHY` in `etl/source_entities.py` | GENERALIZES `rationale` |
| Institution list (83 names, 82 occur) | `INSTITUTIONS` | Institution `extraction` |
| Algorithm and system names | `etl/sota_entities.py` | `extraction` |
| Problem type | keyword rules, then `TOPIC_PROBLEM_TYPE` | `problem_type_method`, CLASSIFIED_AS `evidence` |
| Technique family | name rules, then `TOPIC_TECHNIQUE_FAMILY` | `family_method`, `family_evidence` |
| Model class | `MODELS` | CLASSIFIED_AS `evidence` |
| Gap verdict | the page's bold phrase, else keyword rules | `verdict_method`, `verdict_raw` |
| Bound kind, venue kind, name form | `etl/classify.py` | the property itself |
| Related problems | shared papers and concepts, Jaccard score | RELATED_TO `method`, `score`, `shared_papers`, `shared_concepts` |

None of these has been reviewed by a domain expert yet. Their assignments are `rule-based`.

## What the graph does not contain

- **No identity resolution.** A Person is a name as written. The catalog often gives a surname only,
  so "Wang" is many people and "T. Neumann", "Thomas Neumann" and "Neumann" are three nodes. No
  DBLP or ORCID lookup is made.
- **No citation counts.** A paper's count is the number of catalog pages that cite it, nothing more.
- **Nothing after 2026-09-09.** Whether a problem has been solved since is not known.
- **No funding.**
- **No vectors.** Similar problems by meaning (scope question 39) need embeddings, which this build
  does not compute.

## Limits of the data

- **334 citations do not parse** (`parse_status = uncertain`); their text is kept and no title is
  made up. 364 papers have no year.
- **Venue names are as written.** 150 of 677 are kind `other`, and some of those are fragments of
  the citation rather than a venue.
- **Affiliations are what the page states.** "Suciu, Abo Khamis, Ngo (RelationalAI/UW)" links Ngo,
  the name next to the bracket, to UW. The page says so; whether it is right is not checked.
- **Merged papers depend on the citation text.** Two citations are one paper when an identifier, or
  the title and year, agree. A paper cited with different titles and no identifier stays two.

## What is left out, and counted

`python -m etl.quality` measures each of these, and the
[quality report](../benchmarks/quality-report.md) gives the figures.

| Left out | Why |
|---|---|
| Citations such as "Yannakakis (1981)" as algorithms | a citation is not an algorithm |
| Names not on the institution list | "Pavlo" and "learned optimizers" are not institutions |
| Several names before several institutions in one bracket | the page does not say who is where |
| A second spelling of an author on the same paper | one author list per paper, the most complete |
| Codes no record uses | kept as TaxonomyTerm nodes with no edge, listed in [`taxonomy.md`](taxonomy.md) |

## The 2026-09 reference graph

The graph published before this one, `dbms-research.sgsnap` (kg-snapshots-v10), is not this graph.
`python -m etl.local_graph build --snapshot <path>` imports it into a SQLite file of its own for
comparison, and the quality report compares the two.
