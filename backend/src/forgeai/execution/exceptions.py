class PatchValidationError(Exception):
    """Raised when a proposed code patch fails validation."""


class FileSnapshotError(Exception):
    """Raised when a repository file cannot be safely snapshotted."""


class FileIntegrityError(Exception):
    """Raised when a repository file differs from its expected snapshot."""


class PatchApplicationError(Exception):
    """Raised when a validated patch cannot be safely applied."""
