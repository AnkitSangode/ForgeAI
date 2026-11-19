
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ForgeAI Addition Server")


@mcp.tool()
def add_numbers(a: int, b: int) -> int:
    """Add two integers and return their sum."""
    return a + b


if __name__ == "__main__":
    mcp.run(transport="stdio")
