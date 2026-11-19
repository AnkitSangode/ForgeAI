
from __future__ import annotations

import os
import shutil
import sys

from forgeai.infrastructure.mcp import MCPServerConfig


def create_playwright_server_config() -> MCPServerConfig:
    """Create an isolated Playwright MCP server configuration."""

    if sys.platform == "win32":
        command = shutil.which("npx.cmd") or shutil.which("npx")

        if command is None:
            raise RuntimeError(
                "npx was not found. Install Node.js and npm first."
            )
    else:
        command = shutil.which("npx")

        if command is None:
            raise RuntimeError(
                "npx was not found. Install Node.js and npm first."
            )

    return MCPServerConfig(
        name="playwright",
        command=command,
        args=(
            "-y",
            "@playwright/mcp@latest",
            "--browser",
            "chromium",
            "--headless",
            "--isolated",
        ),
        env=dict(os.environ),
    )
