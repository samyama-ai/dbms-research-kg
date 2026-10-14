# Phase 1 log — understand the domain

Work log for the DBMS Research KG, following *How to Build a Samyama KG* (Phase 1).
Tracking issue: #1. Newest entry first.

## 2026-10-14 — set-up, reading, old graph measured, scope and schema drafted

**Who:** Krithi, after being asked to replicate the existing DBMS Research KG in this repo
and improve its ontology, taxonomy, coding systems and standards, as was done for
ai-research-kg.

### What was done

1. **Opened the tracking issue** #1, "DBMS Research KG: Phase 1, scope and schema review".
2. **Cloned this repo** (created 2026-10-13 from `kg-repo-template`, one commit) and made the
   branch `phase1-scope-and-schema`.
3. **Cloned the data** `github.com/samyama-ai/dbms_research` into `data/dbms_research`.
   `data/` is git-ignored, so the catalog is never committed here.
4. **Pinned the data version** in `data/dbms_research.lock.json`:

   | Field | Value |
   |---|---|
   | commit | `5fff7f74508a52ac238f3bb608b8c8c872489fec` |
   | commit date | 2026-09-09 |
   | fetched | 2026-10-14 |
   | problem pages | 1,053 in 35 topic folders |

   The lock file lives in git-ignored `data/`, so it exists only on this machine for now. A
   download script that writes it (as `etl/download_data.py` does in ai-research-kg) is
   planned for the build phase.
5. **Read the catalog's guide files:** `TAXONOMY.md` (35 topics), `TEMPLATE.md` (page layout),
   `USING_WITH_SAMYAMA_GRAPH.md` (the old graph), and the page
   `topics/01-relational-theory/acyclic-join-dependencies.md` as a worked sample.
6. **Loaded the old graph** `dbms-research.sgsnap` (kg-snapshots-v10, iteration 2026-09) into
   a local engine: Docker container `samyama-dbms_research`, image
   `ghcr.io/samyama-ai/samyama-graph:latest` (engine 1.11.0), port 8092. Import took about
   3 seconds: 20,019 nodes and 39,393 edges, 12 labels, 13 edge types.
7. **Ran test queries** on it. All matched the catalog: 1,053 problems; status open 450,
   partially-solved 369, empirically-open 227, solved-but-impractical 7; the sample page
   cites 6 papers; the most cited paper is *Foundations of Databases* (64 problems).
8. **Wrote [scope.md](scope.md):** 48 questions in 8 groups, each marked [old] (the old graph
   answers it, 27), [partly] (it answers badly, 13) or [new] (it cannot, 8). Every mark was
   checked with a query on the old graph.
9. **Wrote [schema.md](schema.md) v0.1:** a plan with 15 node labels and 16 edge types, the
   old graph's 12 labels plus `Gap`, `ResearchDirection` and `DataSource`.

### The old graph, measured

| Label | Nodes | | Edge | Edges |
|---|---:|---|---|---:|
| Person | 5,193 | | AUTHORED_BY | 10,178 |
| FutureDirection | 3,825 | | CITES | 6,116 |
| Paper | 2,962 | | APPEARED_AT | 5,824 |
| Algorithm | 2,808 | | STATE_OF_ART | 4,086 |
| Bound | 2,106 | | CLOSING_REQUIRES | 3,825 |
| Institution | 1,407 | | HAS_BOUND | 2,106 |
| Problem | 1,053 | | IN_MODEL | 1,887 |
| Venue | 480 | | AFFILIATED_WITH | 1,558 |
| System | 108 | | ACTIVE_ON | 1,275 |
| Topic | 35 | | IN_TOPIC | 1,053 |
| Concept | 34 | | RESTS_ON | 1,043 |
| ComputationModel | 8 | | RELATED_TO | 441 |
| | | | GENERALIZES | 1 |
| **Total** | **20,019** | | **Total** | **39,393** |

### Findings

**In the old graph:**

1. **§6 The Gap is missing.** No node or property holds it, although it is the section that
   says what is unsolved.
2. **§7 Current Research is only partly there.** The people it names become `ACTIVE_ON` links
   (1,272 of the 1,275 links point to a person whose surname appears in that problem's §7).
   The research directions and the labs named there are lost.
3. **Years are text.** `Paper.year` is `"1983"`, not 1983, so year comparisons and sorting
   go wrong.
4. **The reference role sits on the paper.** `Paper.tag` (Foundational, SOTA, Survey) is
   stored once per paper, but a paper can play different roles for different problems.
5. **Edge properties are all called `prop`.** On `AUTHORED_BY` it is the author position
   (counted from 0), on `APPEARED_AT` the year, on `HAS_BOUND` the direction, on
   `STATE_OF_ART` theory or systems.
6. **Institution nodes include non-institutions.** By number of active problems, the top
   three are "Pavlo" (a surname), "Bao" (a system) and "learned optimizers" (a topic).
7. **Algorithm nodes are mostly citations,** for example "Yannakakis (1981)" and
   "Fagin (1983)".
8. **Concepts are thin:** 34 Concept nodes for 1,053 problems, and 1 `GENERALIZES` edge.
9. **Bounds are one per section.** Each problem has exactly one upper and one lower Bound
   (1,053 each). §4 and §5 are mostly paragraphs: only 681 upper-bound and 1,175
   lower-bound bullets exist across all pages.
10. **Ids are counters** (`paper:0`, `bound:0`), so they change when the input changes.
11. **No provenance fields** on any node.

**In the catalog:**

12. Pages have a **10th section, "Worked Example"**, which `TEMPLATE.md` does not list.
13. §9 uses tags the template doesn't list: `[Systems]` 11 times and `[Attack]` twice,
    besides Foundational 2,777, SOTA 2,633, Survey 676, Docs 5 and Artifact 2.
14. **§6 The Gap is prose.** Only 140 of 1,053 pages open it with a bold phrase, most of them
    verdicts such as "Open" or "Partially solved".
15. **No page uses status `stale`,** although the template allows it.
16. All 1,053 pages have `first_added: 2026-06`. `last_reviewed` is 2026-06 for 1,019 pages,
    2026-07 for 6 and 2026-09 for 28.
17. §8 Future Work has 3,825 bullets, exactly the old graph's FutureDirection count. That
    part of the old extraction is complete.

**Docs that don't match the snapshot:**

18. `USING_WITH_SAMYAMA_GRAPH.md` says 3,939 researchers; the snapshot has 5,193 Person nodes.
19. It says 1,966 people carry a DBLP id; the snapshot has 2,034.
20. Its import example shows 18,881 nodes and 39,142 edges; the snapshot imports
    20,019 and 39,393.

### Open questions 

1. Build v1 from the catalog only, and add DBLP lookups as a second step? Proposed: yes.
2. Keep the Problem embeddings in v1, or wait for vector search on imported snapshots
   (samyama-graph#5)? Proposed: leave them out of v1.
3. Who reviews the Concept list and its hierarchy?
4. Should findings 12, 13 and 18–20 be raised as issues on `samyama-ai/dbms_research`?

### Next

Push this branch and open the Phase 1 pull request (Refs #1). After review, Phase 2:
environment and a download script that writes the lock file.
