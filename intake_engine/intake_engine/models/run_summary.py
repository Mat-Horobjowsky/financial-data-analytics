from pydantic import BaseModel


class RunSummary(BaseModel):
    files_found: int
    files_processed: int
    files_failed: int
    file_names_processed: list[str]
    rows_loaded_total: int
    rows_output_total: int
    duplicates_removed_total: int
    warnings_total: int
    failed_files: dict[str, str]  # filename -> error message
    files_failed_validation: int = 0
    files_export_blocked: int = 0
    run_timestamp: str
