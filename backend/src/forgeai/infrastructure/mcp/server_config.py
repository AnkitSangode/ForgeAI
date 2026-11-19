
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class MCPServerConfig:
    """Trusted configuration for one locally launched MCP server."""

    name: str
    command: str
    args: tuple[str, ...] = ()
    env: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("MCP server name cannot be empty.")

        if not isinstance(self.command, str) or not self.command.strip():
            raise ValueError("MCP server command cannot be empty.")

        if not isinstance(self.args, (tuple, list)):
            raise TypeError("MCP server arguments must be a tuple or list.")

        normalized_args = tuple(self.args)

        if any(
            not isinstance(arg, str) or not arg
            for arg in normalized_args
        ):
            raise ValueError(
                "MCP server arguments must be non-empty strings."
            )

        if not isinstance(self.env, Mapping):
            raise TypeError("MCP environment must be a mapping.")

        normalized_env = dict(self.env)

        if any(
            not isinstance(key, str)
            or not key.strip()
            or not isinstance(value, str)
            for key, value in normalized_env.items()
        ):
            raise ValueError(
                "MCP environment must contain non-empty string keys "
                "and string values."
            )

        object.__setattr__(self, "args", normalized_args)
        object.__setattr__(
            self,
            "env",
            MappingProxyType(normalized_env),
        )
