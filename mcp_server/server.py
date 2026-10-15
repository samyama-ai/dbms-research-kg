"""MCP server exposing the DBMS Research KG. Run: python -m mcp_server.server"""
from fastmcp import FastMCP
mcp = FastMCP("dbms-research-kg")

@mcp.tool()
def example_query(limit: int = 5) -> list[dict]:
    """Replace with a real domain query against the Samyama graph engine."""
    return []

if __name__ == "__main__":
    mcp.run()
