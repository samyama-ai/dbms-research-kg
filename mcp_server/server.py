"""MCP server exposing the DBMS Research KG. Run: python -m mcp_server.server

Reads mcp_server/config.yaml for the engine URL. The tools run read-only Cypher.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from fastmcp import FastMCP

CONFIG_PATH = Path(__file__).with_name("config.yaml")


def load_config(path: Path = CONFIG_PATH) -> dict:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not config.get("graph", {}).get("url"):
        raise ValueError(f"{path}: graph.url is required")
    return config


CONFIG = load_config()
mcp = FastMCP(CONFIG["server"]["name"])


@lru_cache(maxsize=1)
def client():
    from samyama import SamyamaClient
    return SamyamaClient.connect(CONFIG["graph"]["url"])


def rows(query: str) -> list[dict]:
    result = client().query_readonly(query)
    return [dict(zip(result.columns, record, strict=False)) for record in result.records]


@mcp.tool()
def problems_in_topic(topic_id: str, limit: int = 20) -> list[dict]:
    """Problems in one topic, e.g. '02-query-optimization', with their status."""
    limit = max(1, min(int(limit), 200))
    topic_id = topic_id.replace("'", "")
    return rows(f"MATCH (p:Problem)-[:IN_TOPIC]->(t:Topic) WHERE t.id = '{topic_id}' OR t.slug = '{topic_id}' "
                f"RETURN p.id AS id, p.title AS title, p.status AS status ORDER BY id LIMIT {limit}")


@mcp.tool()
def most_cited_papers(limit: int = 10) -> list[dict]:
    """Papers cited by the most problems in the catalog."""
    limit = max(1, min(int(limit), 100))
    return rows("MATCH (p:Problem)-[:CITES]->(paper:Paper) RETURN paper.title AS title, "
                f"count(p) AS problems ORDER BY problems DESC LIMIT {limit}")


if __name__ == "__main__":
    mcp.run()
