
from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from psycopg import sql
from psycopg.rows import dict_row

mcp = FastMCP("ForgeAI PostgreSQL MCP Server")

BACKEND_ROOT = Path(__file__).resolve().parents[5]
load_dotenv(BACKEND_ROOT / ".env")

DATABASE_URL = os.getenv("MCP_DATABASE_READONLY_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "MCP_DATABASE_READONLY_URL environment variable is required."
    )

SCHEMA_NAME = "public"
MAX_LIMIT = 100
STATEMENT_TIMEOUT = "10s"


def _get_connection() -> psycopg.Connection:
    """Create a PostgreSQL connection with read-only transaction defaults."""

    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
        connect_timeout=10,
    )


def _execute_readonly(query: sql.Composable, params: tuple = ()) -> list[dict]:
    """Execute one query inside a read-only, time-limited transaction."""

    with _get_connection() as connection, connection.transaction():
        connection.execute("SET TRANSACTION READ ONLY")
        connection.execute(
            sql.SQL("SET LOCAL statement_timeout = {}").format(
                sql.Literal(STATEMENT_TIMEOUT)
            )
        )

        cursor = connection.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def _validate_table_name(table_name: str) -> str:
    """Ensure the requested table exists in the permitted schema."""

    if not isinstance(table_name, str) or not table_name.strip():
        raise ValueError("A valid table name is required.")

    query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s
          AND table_name = %s
          AND table_type = 'BASE TABLE'
    """

    rows = _execute_readonly(
        sql.SQL(query),
        (SCHEMA_NAME, table_name),
    )

    if not rows:
        raise ValueError(
            f"Table '{table_name}' does not exist in schema '{SCHEMA_NAME}'."
        )

    return table_name


@mcp.tool()
def list_tables() -> str:
    """List all accessible base tables in the public schema."""

    query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """

    rows = _execute_readonly(
        sql.SQL(query),
        (SCHEMA_NAME,),
    )

    return json.dumps(
        {"schema": SCHEMA_NAME, "tables": rows},
        default=str,
    )


@mcp.tool()
def describe_table(table_name: str) -> str:
    """Describe columns, data types, and nullability of a public table."""

    table_name = _validate_table_name(table_name)

    query = """
        SELECT
            column_name,
            data_type,
            is_nullable,
            column_default,
            ordinal_position
        FROM information_schema.columns
        WHERE table_schema = %s
          AND table_name = %s
        ORDER BY ordinal_position
    """

    rows = _execute_readonly(
        sql.SQL(query),
        (SCHEMA_NAME, table_name),
    )

    return json.dumps(
        {
            "table": table_name,
            "schema": SCHEMA_NAME,
            "columns": rows,
        },
        default=str,
    )


@mcp.tool()
def read_records(
    table_name: str,
    limit: int = 20,
    offset: int = 0,
) -> str:
    """Read records from a public table with pagination.

    This tool only supports reading. It does not accept arbitrary SQL.
    """

    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("Limit must be an integer.")

    if isinstance(offset, bool) or not isinstance(offset, int):
        raise ValueError("Offset must be an integer.")

    if not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"Limit must be between 1 and {MAX_LIMIT}.")

    if offset < 0:
        raise ValueError("Offset cannot be negative.")

    table_name = _validate_table_name(table_name)

    query = sql.SQL(
        "SELECT * FROM {}.{} LIMIT %s OFFSET %s"
    ).format(
        sql.Identifier(SCHEMA_NAME),
        sql.Identifier(table_name),
    )

    rows = _execute_readonly(
        query,
        (limit, offset),
    )

    return json.dumps(
        {
            "table": table_name,
            "limit": limit,
            "offset": offset,
            "returned_records": len(rows),
            "records": rows,
        },
        default=str,
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
