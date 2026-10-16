// The 48 scope questions of benchmarks/scope.md as Cypher, run against the loaded graph.
// Run them with `python -m benchmarks.run --url http://127.0.0.1:8094`, which writes
// benchmarks/scope_questions.md with each answer beside the verdict of the raw-page check
// (python -m benchmarks.reference).
//
// Samples, the same as benchmarks/reference.py: problem 01-relational-theory/acyclic-join-dependencies,
// person "T. Neumann", concept "AGM bound", institution Carnegie Mellon University (Q13 uses the first
// page whose Current Research names it). Questions 46-48 must return no rows: the catalog has no such data.
// Q39 has no Cypher: it needs vector search (see the demo pack's vector segment).

// Q1 · What are the 35 DBMS topics?
MATCH (t:Topic) RETURN t.number AS number, t.name AS topic ORDER BY number

// Q2 · How many problems are there, and how many are open?
MATCH (p:Problem) RETURN count(p) AS problems, sum(CASE WHEN p.status = "open" THEN 1 ELSE 0 END) AS open

// Q3 · How many problems are in each topic?
MATCH (p:Problem)-[:IN_TOPIC]->(t:Topic) RETURN t.name AS topic, count(p) AS problems ORDER BY problems DESC, topic

// Q4 · Which topics have the most open problems?
MATCH (p:Problem {status: "open"})-[:IN_TOPIC]->(t:Topic) RETURN t.name AS topic, count(p) AS open_problems ORDER BY open_problems DESC, topic

// Q5 · Which problems are solved but impractical?
MATCH (p:Problem {status: "solved-but-impractical"})-[:IN_TOPIC]->(t:Topic) RETURN p.title AS problem, t.name AS topic ORDER BY topic, problem

// Q6 · Which problems were last reviewed before a given iteration (2026-07)?
MATCH (p:Problem) WHERE p.last_reviewed < "2026-07" RETURN count(p) AS problems

// Q7 · What does problem X state, and what is its status?
MATCH (p:Problem {id: "01-relational-theory/acyclic-join-dependencies"}) RETURN p.title AS title, p.status AS status, left(p.statement, 120) AS statement

// Q8 · Which topic does problem X belong to?
MATCH (p:Problem {id: "01-relational-theory/acyclic-join-dependencies"})-[:IN_TOPIC]->(t:Topic) RETURN t.name AS topic

// Q9 · Which papers does problem X cite, and in what role?
MATCH (p:Problem {id: "01-relational-theory/acyclic-join-dependencies"})-[c:CITES]->(x:Paper) RETURN c.position AS position, c.role AS role, x.title AS paper ORDER BY position

// Q10 · What are the best-known upper and lower bounds for problem X, and in which model?
MATCH (p:Problem {id: "01-relational-theory/acyclic-join-dependencies"})-[:HAS_BOUND]->(b:Bound) OPTIONAL MATCH (b)-[:IN_MODEL]->(m:ComputationModel) RETURN b.direction AS bound, b.kind AS kind, collect(m.name) AS models ORDER BY bound DESC

// Q11 · What is the gap between the upper and lower bound for problem X?
MATCH (p:Problem {id: "01-relational-theory/acyclic-join-dependencies"})-[:HAS_GAP]->(g:Gap) RETURN g.verdict AS verdict, g.verdict_method AS decided_by, left(g.text, 120) AS gap

// Q12 · Which researchers are named as working on problem X right now?
MATCH (a:Person)-[:ACTIVE_ON]->(p:Problem {id: "01-relational-theory/acyclic-join-dependencies"}) RETURN a.name AS researcher ORDER BY researcher

// Q13 · Which labs or groups are named as working on problem X?
MATCH (i:Institution)-[r:ACTIVE_ON]->(p:Problem {id: "02-query-optimization/adaptive-reoptimization"}) RETURN i.name AS lab, i.kind AS kind ORDER BY lab

// Q14 · What is the worked example for problem X?
MATCH (p:Problem {id: "01-relational-theory/acyclic-join-dependencies"}) RETURN size(p.worked_example) AS characters, left(p.worked_example, 80) AS starts

// Q15 · What future work would move problem X forward?
MATCH (p:Problem {id: "01-relational-theory/acyclic-join-dependencies"})-[c:CLOSING_REQUIRES]->(f:FutureDirection) RETURN c.position + 1 AS step, f.text AS future_work ORDER BY step

// Q16 · Which papers are cited by the most problems?
MATCH (p:Problem)-[:CITES]->(x:Paper) RETURN x.title AS paper, x.year AS year, count(p) AS problems ORDER BY problems DESC, paper LIMIT 10

// Q17 · Which papers are cited across the most topics?
MATCH (p:Problem)-[:CITES]->(x:Paper), (p)-[:IN_TOPIC]->(t:Topic) RETURN x.title AS paper, count(DISTINCT t) AS topics ORDER BY topics DESC, paper LIMIT 10

// Q18 · Which surveys cover the most problems?
MATCH (p:Problem)-[c:CITES {role: "survey"}]->(x:Paper) RETURN x.title AS survey, count(p) AS problems ORDER BY problems DESC, survey LIMIT 10

// Q19 · How many cited papers appeared after a given year (2015), and in each decade?
MATCH (x:Paper) WHERE x.year IS NOT NULL RETURN (x.year / 10) * 10 AS decade, count(x) AS papers, sum(CASE WHEN x.year > 2015 THEN 1 ELSE 0 END) AS after_2015 ORDER BY decade

// Q20 · Which venues publish the most cited papers?
MATCH (x:Paper)-[:APPEARED_AT]->(v:Venue) RETURN v.name AS venue, v.kind AS kind, count(x) AS papers ORDER BY papers DESC, venue LIMIT 10

// Q21 · Which papers have a DOI, an arXiv id, or only a DBLP record?
MATCH (x:Paper) RETURN sum(CASE WHEN x.doi <> "" THEN 1 ELSE 0 END) AS doi, sum(CASE WHEN x.arxiv_id <> "" THEN 1 ELSE 0 END) AS arxiv, sum(CASE WHEN x.dblp_key <> "" AND x.doi = "" AND x.arxiv_id = "" THEN 1 ELSE 0 END) AS dblp_only, count(x) AS papers

// Q22 · Which references could not be verified against any bibliographic source?
MATCH (p:Problem)-[c:CITES {verification_status: "unverified"}]->(x:Paper) RETURN p.title AS problem, x.title AS paper ORDER BY problem

// Q23 · Which researchers wrote the most cited papers?
MATCH (x:Paper)-[:AUTHORED_BY]->(a:Person) RETURN a.name AS researcher, a.name_form AS written_as, count(x) AS papers ORDER BY papers DESC, researcher LIMIT 10

// Q24 · Which researchers are active on the most problems, and across the most topics?
MATCH (a:Person)-[:ACTIVE_ON]->(p:Problem)-[:IN_TOPIC]->(t:Topic) RETURN a.name AS researcher, count(DISTINCT p) AS problems, count(DISTINCT t) AS topics ORDER BY problems DESC, researcher LIMIT 10

// Q25 · Who does researcher X co-author with most often?
MATCH (a:Person {name: "T. Neumann"})<-[:AUTHORED_BY]-(x:Paper)-[:AUTHORED_BY]->(b:Person) WHERE b <> a RETURN b.name AS coauthor, count(x) AS shared_papers ORDER BY shared_papers DESC, coauthor LIMIT 10

// Q26 · Which researchers have a DBLP or ORCID profile?
MATCH (a:Person) WHERE a.dblp_pid IS NOT NULL OR a.orcid IS NOT NULL RETURN a.name AS researcher, a.dblp_pid AS dblp, a.orcid AS orcid LIMIT 10

// Q27 · Which institutions have the most researchers active on open problems?
MATCH (i:Institution)-[:ACTIVE_ON]->(p:Problem {status: "open"}) RETURN i.name AS institution, i.kind AS kind, count(p) AS open_problems ORDER BY open_problems DESC, institution LIMIT 10

// Q28 · Are name variants of the same person merged into one node?
MATCH (a:Person) WHERE a.name ENDS WITH "Neumann" RETURN a.name AS written_as, a.name_form AS form ORDER BY written_as

// Q29 · Which algorithms are state of the art for the most problems?
MATCH (p:Problem)-[:STATE_OF_ART]->(s:Algorithm) RETURN s.name AS algorithm, s.family AS family, count(p) AS problems ORDER BY problems DESC, algorithm LIMIT 10

// Q30 · Which production systems are named as state of the art?
MATCH (p:Problem)-[:STATE_OF_ART]->(s:System) RETURN s.name AS system, s.family AS family, count(p) AS problems ORDER BY problems DESC, system LIMIT 10

// Q31 · For problem X, what is the theory SOTA and what is the systems SOTA?
MATCH (p:Problem {id: "01-relational-theory/acyclic-join-dependencies"})-[r:STATE_OF_ART]->(s) RETURN r.kind AS kind, s.name AS name ORDER BY kind, name

// Q32 · Which problems have a lower bound conditional on SETH or another fine-grained hypothesis?
MATCH (p:Problem)-[:HAS_BOUND]->(:Bound {direction: "lower"})-[:IN_MODEL]->(:ComputationModel {class: "fine-grained"}) RETURN count(DISTINCT p) AS problems

// Q33 · Which problems have a time bound, a space bound, or an impossibility result?
MATCH (b:Bound) RETURN b.kind AS kind, count(b) AS bounds ORDER BY bounds DESC

// Q34 · Which problems have matching upper and lower bounds, so they are closed in theory?
MATCH (p:Problem)-[:HAS_GAP]->(g:Gap {verdict: "closed"}) RETURN p.title AS problem, g.verdict_method AS decided_by ORDER BY problem

// Q35 · Which problems are related to problem X?
MATCH (p:Problem {id: "01-relational-theory/acyclic-join-dependencies"})-[r:RELATED_TO]-(q:Problem) RETURN q.title AS related, r.shared_papers AS shared_papers, r.score AS score ORDER BY score DESC, related

// Q36 · Which pairs of topics are most strongly connected?
MATCH (a:Problem)-[:RELATED_TO]->(b:Problem), (a)-[:IN_TOPIC]->(s:Topic), (b)-[:IN_TOPIC]->(t:Topic) WHERE s <> t RETURN CASE WHEN s.name < t.name THEN s.name ELSE t.name END AS topic_a, CASE WHEN s.name < t.name THEN t.name ELSE s.name END AS topic_b, count(*) AS links ORDER BY links DESC LIMIT 10

// Q37 · Which problems rest on the same mathematical concept (the AGM bound)?
MATCH (p:Problem)-[:RESTS_ON]->(c:Concept {name: "AGM bound"}) RETURN count(p) AS problems

// Q38 · Which concepts generalise which?
MATCH (a:Concept)-[:GENERALIZES]->(b:Concept) RETURN a.name AS broader, b.name AS narrower ORDER BY broader, narrower

// Q40 · Which problems bridge otherwise unrelated topics?
MATCH (p:Problem)-[:RELATED_TO]-(q:Problem)-[:IN_TOPIC]->(t:Topic), (p)-[:IN_TOPIC]->(own:Topic) WHERE t <> own RETURN p.title AS problem, count(DISTINCT t) AS other_topics ORDER BY other_topics DESC, problem LIMIT 10

// Q41 · Which open problems have an open gap between upper and lower bound?
MATCH (p:Problem {status: "open"})-[:HAS_GAP]->(g:Gap {verdict: "open"}) RETURN count(p) AS problems

// Q42 · Which open problems have no researcher named as working on them?
MATCH (p:Problem {status: "open"}) WHERE NOT (:Person)-[:ACTIVE_ON]->(p) RETURN count(p) AS problems

// Q43 · Which topics have the most future-work items?
MATCH (p:Problem)-[:CLOSING_REQUIRES]->(f:FutureDirection), (p)-[:IN_TOPIC]->(t:Topic) RETURN t.name AS topic, count(f) AS future_work ORDER BY future_work DESC, topic LIMIT 10

// Q44 · Which future directions are shared by several problems?
MATCH (p:Problem)-[:CLOSING_REQUIRES]->(f:FutureDirection) WITH f.text AS text, count(DISTINCT p) AS problems WHERE problems > 1 RETURN text, problems

// Q45 · Which open problems cite nothing published after 2015?
MATCH (p:Problem {status: "open"})-[:CITES]->(x:Paper) WITH p, sum(CASE WHEN x.year > 2015 THEN 1 ELSE 0 END) AS recent WHERE recent = 0 RETURN count(p) AS problems

// Q46 · How many citations does paper X have in total? (must return nothing)
MATCH (x:Paper) WHERE x.citation_count IS NOT NULL RETURN x.title AS paper, x.citation_count AS citations LIMIT 5

// Q47 · Has problem X been solved since the catalog was written? (must return nothing)
MATCH (p:Problem) WHERE p.solved_on IS NOT NULL RETURN p.title AS problem, p.solved_on AS solved LIMIT 5

// Q48 · Who funds the work on problem X? (must return nothing)
MATCH (p:Problem) WHERE p.funding IS NOT NULL RETURN p.title AS problem, p.funding AS funding LIMIT 5
