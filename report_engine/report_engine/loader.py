from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


class LoaderError(Exception):
    pass


@dataclass
class ReportData:
    input_dir: Path
    validation_status: str
    validation_errors: list[str]
    validation_warnings: list[str]
    long_metrics: pd.DataFrame
    wide_metrics: pd.DataFrame
    metric_dictionary: pd.DataFrame


def load(input_dir: str | Path) -> ReportData:
    d = Path(input_dir)
    if not d.exists():
        raise LoaderError(f"Input directory not found: {d}")
    if not d.is_dir():
        raise LoaderError(f"Input path is not a directory: {d}")

    vr_path = d / "validation_report.json"
    if not vr_path.exists():
        raise LoaderError(f"Required file missing: {vr_path}")
    vr = json.loads(vr_path.read_text(encoding="utf-8"))

    def _load_csv(name: str) -> pd.DataFrame:
        p = d / name
        return pd.read_csv(p) if p.exists() else pd.DataFrame()

    return ReportData(
        input_dir=d,
        validation_status=vr.get("status", "unknown"),
        validation_errors=vr.get("errors", []),
        validation_warnings=vr.get("warnings", []),
        long_metrics=_load_csv("long_metrics.csv"),
        wide_metrics=_load_csv("wide_metrics.csv"),
        metric_dictionary=_load_csv("metric_dictionary.csv"),
    )
