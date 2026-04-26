class IntakeError(Exception):
    """Base exception for intake_engine."""


class LoadError(IntakeError):
    """Raised when a file cannot be loaded."""


class ExportError(IntakeError):
    """Raised when output cannot be written."""


class DBError(IntakeError):
    """Raised when a DuckDB operation fails."""
