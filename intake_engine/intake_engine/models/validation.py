from pydantic import BaseModel


class ValidationReport(BaseModel):
    file_name: str
    status: str  # "pass", "warn", "fail"
    issues: list[str]
    warnings: list[str]
    rows_loaded: int   # pre-clean row count
    row_count: int     # post-clean row count
    columns: int
    duplicate_rate: float
    null_summary: dict[str, float]  # column -> null rate (0.0–1.0), keyed on clean names
    run_timestamp: str
