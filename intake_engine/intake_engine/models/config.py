from pathlib import Path

from pydantic import BaseModel


class ColumnRule(BaseModel):
    rename: str | None = None       # canonical name to use after cleaning
    type: str | None = None         # expected type: "date" | "numeric" | "string"
    nullable: bool = True           # set False to warn when column contains nulls


class PipelineConfig(BaseModel):
    required_columns: list[str] = []
    null_threshold: float = 0.3
    duplicate_threshold: float = 0.3
    output_format: str = "csv"   # "csv" | "parquet"
    output_dir: str = "outputs"
    run_validate: bool = False
    run_profile: bool = False
    block_export_on_fail: bool = False
    sheet: str | None = None     # sheet name or "all"; None → first sheet (Excel only)
    columns: dict[str, ColumnRule] = {}  # per-column rename/type/nullable rules
    db_mode: str = "replace"     # "replace" | "append"
    select_columns: list[str] = []  # output column whitelist + order; empty = all


def load_config(path: Path) -> PipelineConfig:
    """Load a YAML pipeline config file and return a PipelineConfig."""
    try:
        import yaml
    except ImportError as exc:
        raise ImportError(
            "PyYAML is required for --config support. Install it with: pip install pyyaml"
        ) from exc

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return PipelineConfig(**raw)
