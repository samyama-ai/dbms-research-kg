// The ten queries of the demo, in the order it runs them.
// Written by `python -m demo.demo --write-cypher`. Do not edit: edit STORY in demo/demo.py.

// 1. How open is the field?  (rests on: parsed)
// 1,053 problems, one catalog page each. Their status, as the page header states it.
MATCH (p:Problem) RETURN p.status AS status, count(p) AS problems ORDER BY problems DESC;

// 2. Which topics have the most open problems?  (rests on: parsed)
// The 35 topics of TAXONOMY.md; every problem sits in exactly one.
MATCH (p:Problem {status: 'open'})-[:IN_TOPIC]->(t:Topic) RETURN t.name AS topic, count(p) AS open_problems ORDER BY open_problems DESC, topic LIMIT 5;

// 3. Which papers are cited by the most problems?  (rests on: parsed)
// One node per paper: citations by DOI, arXiv id, DBLP key or title and year are merged.
MATCH (p:Problem)-[:CITES]->(x:Paper) RETURN x.title AS paper, x.year AS year, count(p) AS problems ORDER BY problems DESC, paper LIMIT 5;

// 4. Which labs are named on the most open problems?  (rests on: rule)
// Labs named in 'Current Research', matched against a checked list of 84 institutions.
MATCH (i:Institution)-[:ACTIVE_ON]->(p:Problem {status: 'open'}) RETURN i.name AS institution, i.kind AS kind, count(p) AS open_problems ORDER BY open_problems DESC, institution LIMIT 6;

// 5. Which systems are state of the art for the most problems?  (rests on: rule)
// Names written in bold in 'State of the Art', labelled by their Theory/Systems bullet.
MATCH (p:Problem)-[:STATE_OF_ART]->(s:System) RETURN s.name AS system, s.family AS family, count(p) AS problems ORDER BY problems DESC, system LIMIT 6;

// 6. Which lower bounds rest on a fine-grained hypothesis such as SETH?  (rests on: rule)
// 'Lower Bound' text matched to computation models; conditional hardness is its own class.
MATCH (p:Problem)-[:HAS_BOUND]->(b:Bound {direction: 'lower'})-[:IN_MODEL]->(m:ComputationModel {class: 'fine-grained'})-[:CLASSIFIED_AS]->(:TaxonomyTerm) MATCH (p)-[:IN_TOPIC]->(t:Topic) RETURN t.name AS topic, count(DISTINCT p) AS problems ORDER BY problems DESC, topic LIMIT 5;

// 7. Where is the gap between the bounds closed, and where is it still open?  (rests on: rule)
// 'The Gap' read for its verdict: the page's own bold word first, otherwise a keyword rule.
MATCH (p:Problem)-[:HAS_GAP]->(g:Gap) RETURN g.verdict AS gap_verdict, count(p) AS problems, sum(CASE WHEN g.verdict_method = 'stated' THEN 1 ELSE 0 END) AS stated_by_the_page ORDER BY problems DESC;

// 8. Which problems are closest to acyclic join dependency recognition?  (rests on: computed)
// Not stated anywhere: computed from shared cited papers and concepts, with a Jaccard score.
MATCH (a:Problem {id: '01-relational-theory/acyclic-join-dependencies'})-[r:RELATED_TO]-(b:Problem) RETURN b.title AS related_problem, r.shared_papers AS shared_papers, r.score AS score ORDER BY score DESC, related_problem LIMIT 5;

// 9. How do the width measures nest?  (rests on: rule)
// Concepts from 'Mathematical Foundations' with a reviewed broader-narrower hierarchy.
MATCH (a:Concept)-[:GENERALIZES]->(b:Concept) WHERE a.name CONTAINS 'width' OR b.name CONTAINS 'width' OR b.name = 'acyclicity' RETURN a.name AS broader, b.name AS narrower ORDER BY broader, narrower;

// 10. How much funding has each problem received?  (rests on: none)
// The catalog says nothing about funding, so the graph says nothing.
MATCH (p:Problem) WHERE p.funding IS NOT NULL RETURN p.title AS problem, p.funding AS funding LIMIT 3;
