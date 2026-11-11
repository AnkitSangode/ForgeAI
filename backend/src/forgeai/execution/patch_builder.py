
from forgeai.agent.coder_schema import CodeChange
from forgeai.execution.exceptions import PatchApplicationError


class PatchBuilder:
    """Builds a deterministic unified patch from code changes."""

    @staticmethod
    def build(changes: list[CodeChange]) -> str:
        """Combine individual unified diffs into one patch."""

        if not changes:
            raise PatchApplicationError(
                "Cannot build a patch without code changes."
            )

        patch_parts = [
            change.unified_diff.rstrip("\n")
            for change in changes
        ]

        return "\n".join(patch_parts) + "\n"
