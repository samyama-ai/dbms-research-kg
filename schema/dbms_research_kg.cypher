// DBMS Research KG — indexes the engine loader creates before writing nodes and edges.
// Run by etl/engine_load.py (python -m etl.loader --load). Schema: docs/schema.md,
// schema/conformance.json (which also declares the ontology mappings).
//
// The engine accepts `CREATE INDEX ON :Label(prop)`, not uniqueness constraints; `id`
// uniqueness is guaranteed by the builder (deterministic ids) and checked by etl.conformance.
// The `id` indexes are what make the edge load finish: every edge endpoint is matched by id.

CREATE INDEX ON :Problem(id);
CREATE INDEX ON :Topic(id);
CREATE INDEX ON :Paper(id);
CREATE INDEX ON :Person(id);
CREATE INDEX ON :Venue(id);
CREATE INDEX ON :Institution(id);
CREATE INDEX ON :Concept(id);
CREATE INDEX ON :Algorithm(id);
CREATE INDEX ON :System(id);
CREATE INDEX ON :Bound(id);
CREATE INDEX ON :ComputationModel(id);
CREATE INDEX ON :Gap(id);
CREATE INDEX ON :ResearchDirection(id);
CREATE INDEX ON :FutureDirection(id);
CREATE INDEX ON :DataSource(id);
CREATE INDEX ON :TaxonomyTerm(id);

// Filters used by the demo queries and the MCP tools
CREATE INDEX ON :Problem(status);
CREATE INDEX ON :Problem(slug);
CREATE INDEX ON :Topic(slug);
CREATE INDEX ON :Paper(title);
CREATE INDEX ON :Person(name);
