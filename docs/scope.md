# dbms-research-kg — scope

## Core question

What are the open problems in database systems research, and how do they connect to
topics, papers, people, algorithms, systems and complexity bounds?

- **Data:** `samyama-ai/dbms_research`, commit `5fff7f7` (2026-09-09), 1,053 problem pages in 35 topics.
- **Status counts:** open 450, partially-solved 369, empirically-open 227, solved-but-impractical 7. No page uses the template's fifth value, `stale`.
- **Reference graph:** the existing snapshot `dbms-research.sgsnap` (kg-snapshots-v10, iteration 2026-09), 20,019 nodes and 39,393 edges. "Old graph" below means this snapshot.

Questions 1–45 carry one mark each: **28 [old], 10 [partly], 7 [new]**. Group H (46–48) is unmarked on purpose, because those are questions the graph must refuse. The marks were checked by running queries on the old graph loaded into a local engine (version 1.11.0) on 2026-10-14.

| Mark | Meaning |
|---|---|
| **[old]** | The old graph already answers it correctly. Our graph must too. |
| **[partly]** | The old graph gives an answer, but it is incomplete or wrong. The note says why. |
| **[new]** | The old graph can't answer it. Our graph adds what is needed. |

The marks compare with the **old** graph. Where our planned graph can answer a question only in part, the note says so (Q34, Q41).


The answers on the catalog-built graph (v6), each checked against the raw pages, are in the [question report](question-report.md).

## A. Problems and topics

1. What are the 35 DBMS topics? **[old]**
2. How many problems are there in total, and how many are open? **[old]**
3. How many problems are in each topic? **[old]**
4. Which topics have the most open problems? **[old]** Self-Driving / Autonomous Databases leads with 22.
5. Which problems are solved but impractical? **[old]**
6. Which problems were last reviewed before a given iteration, or have had no substantive update since? **[new]** The page header's dates (`first_added`, `last_reviewed`, `last_substantive_update`, `refs_checked`) are not in the old graph.

## B. Understanding one problem

7. What does problem X state, and what is its status? **[old]**
8. Which topic does problem X belong to? **[old]**
9. Which papers does problem X cite, and in what role (foundational, SOTA, survey)? **[partly]** The role is stored once on the Paper, but it belongs to the citation: one paper can be foundational for one problem and SOTA for another.
10. What are the best-known upper and lower bounds for problem X, and in which model of computation? **[old]**
11. What is the gap between the bounds, and what would close it? **[new]** Section 6, The Gap, is not in the old graph.
12. Which researchers are named as working on problem X right now? **[old]** From section 7, as `ACTIVE_ON` links.
13. Which labs or groups are named as working on problem X, and on what approach? **[new]** The old graph keeps only person names from section 7.
14. What is the worked example for problem X? **[old]** Stored as text on the Problem.
15. What future work would move problem X forward? **[old]**

## C. Papers

16. Which papers are cited by the most problems? **[old]** *Foundations of Databases*, cited by 64.
17. Which papers are cited across the most topics? **[old]**
18. Which surveys cover the most problems? **[partly]** Same reason as Q9: the survey tag sits on the paper, not on the citation.
19. How many cited papers appeared after a given year, or in each decade? **[partly]** Years are stored as text (`"1983"`), so number comparisons and sorting go wrong.
20. Which venues publish the most cited papers? **[old]** SIGMOD 844, VLDB 599, PODS 342.
21. Which papers have a DOI, an arXiv id, or only a DBLP record? **[new]** The old graph keeps one `url` per paper and no identifier fields.
22. Which references could not be verified against any bibliographic source? **[old]** 13 citations are marked unverified.

## D. Researchers and institutions

23. Which researchers wrote the most cited papers? **[old]**
24. Which researchers are active on the most problems, and across the most topics? **[old]**
25. Who does researcher X co-author with most often? **[old]**
26. Which researchers have a DBLP or ORCID profile? **[old]** 2,034 have a DBLP id.
27. Which institutions have the most researchers active on open problems? **[partly]** Many Institution nodes are not institutions: the top three by active problems are "Pavlo", "Bao" and "learned optimizers".
28. Are name variants of the same person merged into one node, e.g. "M. Yannakakis" and "Mihalis Yannakakis"? **[partly]** Only through DBLP; 5,193 Person nodes remain, many of them initials or bare surnames.

## E. Algorithms, systems and bounds

29. Which algorithms are state of the art for the most problems? **[partly]** Most Algorithm nodes are citations, not algorithms: e.g. "Yannakakis (1981)" and "Fagin (1983)".
30. Which production systems are named as state of the art? **[old]** 108 systems.
31. For problem X, what is the theory SOTA and what is the systems SOTA? **[old]**
32. Which problems have a lower bound conditional on SETH or another fine-grained hypothesis? **[old]** 154 problems.
33. Which problems have a time bound, a space bound, or an impossibility result? **[old]**
34. Which problems have matching upper and lower bounds, so they are closed in theory? **[new]** Needs The Gap from section 6. *Partly answerable in v1:* only where the page states or clearly words the gap as closed (`Gap.verdict`, schema §5); bounds are prose, so matching is not computed.

## F. Connections between problems

35. Which problems are related to problem X? **[old]** 441 `RELATED_TO` links.
36. Which pairs of topics are most strongly connected? **[old]**
37. Which problems rest on the same mathematical concept, e.g. the AGM bound or treewidth? **[partly]** Only 34 Concept nodes exist for 1,053 problems.
38. Which concepts generalise which, e.g. α-acyclicity and β-acyclicity? **[partly]** Only 1 `GENERALIZES` link exists.
39. Which problems are most similar in meaning to a given paragraph? **[partly]** Problems carry embeddings, but vector search on the imported snapshot returns nothing (engine issue samyama-graph#5).
40. Which problems bridge otherwise unrelated topics? **[old]**

## G. Finding research opportunities

41. Which open problems have the widest gap between upper and lower bound? **[new]** Needs section 6. *Partly answerable in v1:* the graph can list open problems whose gap the page calls open or wide (`Gap.verdict`), but it cannot measure or rank gap width, because bounds are prose.
42. Which open problems have no researcher named as working on them? **[old]** 232 open problems.
43. Which topics have the most future-work items? **[old]**
44. Which future directions are shared by several problems? **[new]** Each FutureDirection belongs to one problem, so shared directions never meet.
45. Which open problems cite mostly old work, e.g. nothing after 2015? **[partly]** Years are text, see Q19.

## H. Questions the graph should NOT answer

The graph must return no data for these, rather than guess.

46. How many citations does paper X have in total? The catalog only knows citations from its own pages.
47. Has problem X been solved since the catalog was written? The catalog is a snapshot as of 2026-09.
48. Who funds the work on problem X? The catalog has no funding data.

## Summary of what our graph adds

From the **[partly]** and **[new]** marks above:

| Fix | Questions |
|---|---|
| Add section 6, The Gap | 11, 34, 41 |
| Add labs and approaches from section 7 | 13 |
| Add the header dates | 6 |
| Put the reference role on the citation, not the paper | 9, 18 |
| Store years as numbers | 19, 45 |
| Add paper identifiers: DOI, arXiv, DBLP | 21 |
| Clean up Institution and Algorithm nodes | 27, 29 |
| Better person merging | 28 |
| More Concepts and a concept hierarchy | 37, 38 |
| Shared future directions | 44 |
| Vector search, once the engine bug is fixed | 39 |
