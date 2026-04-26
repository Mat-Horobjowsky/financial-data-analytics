from pydantic import BaseModel


class ProfileReport(BaseModel):
    file_name: str
    rows_loaded: int
    rows_output: int
    columns: int
    column_names: list[str]
    inferred_types: dict[str, str]
    null_counts: dict[str, int]
    duplicate_rows_removed: int
    columns_renamed: dict[str, str]
    numeric_columns_normalized: list[str]
    date_columns_normalized: list[str]
    semantic_types: dict[str, str]
    warnings: list[str]
    run_timestamp: str
