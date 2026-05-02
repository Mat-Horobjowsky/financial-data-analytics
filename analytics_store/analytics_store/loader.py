from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


class LoaderError(Exception):
    pass


@dataclass
class MetricsData:
    metrics_dir: Path
    validation_status: str
    validation_errors: list[str]
    validation_warnings: list[str]
    long_metrics: pd.DataFrame
    wide_metrics: pd.DataFrame
    metric_dictionary: pd.DataFrame


@dataclass
class ReportData:
    report_dir: Path | None
    insights: list[dict]
    summary: dict


def load_metrics(metrics_dir: str | Path) -> MetricsData:
    d = Path(metrics_dir)
    if not d.exists():
        raise LoaderError(f"Metrics directory not found: {d}")
    if not d.is_dir():
        raise LoaderError(f"Metrics path is not a directory: {d}")

    vr_path = d / "validation_report.json"
    if not vr_path.is_file():
        raise LoaderError(f"Required file missing: {vr_path}")
    try:
        vr = json.loads(vr_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LoaderError(f"validation_report.json is not valid JSON: {vr_path}") from exc

    def _load_csv(name: str) -> pd.DataFrame:
        p = d / name
        if not p.exists():
            return pd.DataFrame()
        try:
            return pd.read_csv(p)
        except Exception as exc:
            raise LoaderError(f"Failed to read CSV '{name}': {exc}") from exc

    return MetricsData(
        metrics_dir=d,
        validation_status=vr.get("status", "unknown"),
        validation_errors=vr.get("errors", []),
        validation_warnings=vr.get("warnings", []),
        long_metrics=_load_csv("long_metrics.csv"),
        wide_metrics=_load_csv("wide_metrics.csv"),
        metric_dictionary=_load_csv("metric_dictionary.csv"),
    )


def load_report(report_dir: str | Path | None) -> ReportData:
    if report_dir is None:
        return ReportData(report_dir=None, insights=[], summary={})

    d = Path(report_dir)
    if not d.exists():
        raise LoaderError(f"Report directory not found: {d}")
    if not d.is_dir():
        raise LoaderError(f"Report path is not a directory: {d}")

    insights: list[dict] = []
    insights_path = d / "insights.json"
    if insights_path.is_file():
        try:
            payload = json.loads(insights_path.read_text(encoding="utf-8"))
            insights = payload.get("insights", [])
        except json.JSONDecodeError as exc:
            raise LoaderError(f"insights.json is not valid JSON: {insights_path}") from exc

    summary: dict = {}
    summary_path = d / "summary.json"
    if summary_path.is_file():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise LoaderError(f"summary.json is not valid JSON: {summary_path}") from exc

    return ReportData(report_dir=d, insights=insights, summary=summary)
