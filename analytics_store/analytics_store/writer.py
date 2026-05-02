from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from .loader import MetricsData, ReportData

_LONG_METRICS_COLS = [
    "rollup_level", "date", "provider", "region", "metric_id",
    "label", "value", "unit", "prior_period_value", "period_change", "period_change_pct",
]
_METRIC_DICT_COLS = ["id", "label", "type", "unit", "decimals", "description"]
_REPORT_INSIGHTS_COLS = ["metric_id", "label", "date", "period_change_pct", "direction", "text"]
_REPORT_SUMMARY_COLS = [
    "validation_status", "error_count", "warning_count",
    "template", "metric_count", "date_min", "date_max",
]


def build_store(
    metrics_data: MetricsData,
    report_data: ReportData,
    db_path: str | Path,
) -> list[str]:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    created: list[str] = []
    con = duckdb.connect(str(db_path))
    try:
        _write_df(con, "long_metrics", _ensure_cols(metrics_data.long_metrics, _LONG_METRICS_COLS))
        created.append("long_metrics")

        _write_df(con, "wide_metrics", metrics_data.wide_metrics)
        created.append("wide_metrics")

        _write_df(con, "metric_dictionary", _ensure_cols(metrics_data.metric_dictionary, _METRIC_DICT_COLS))
        created.append("metric_dictionary")

        val_df = pd.DataFrame([{
            "status": metrics_data.validation_status,
            "error_count": len(metrics_data.validation_errors),
            "warning_count": len(metrics_data.validation_warnings),
        }])
        _write_df(con, "metrics_validation_summary", val_df)
        created.append("metrics_validation_summary")

        if report_data.insights:
            insights_df = pd.DataFrame(report_data.insights)
        else:
            insights_df = pd.DataFrame(columns=_REPORT_INSIGHTS_COLS)
        _write_df(con, "report_insights", insights_df)
        created.append("report_insights")

        summary = report_data.summary
        if summary:
            date_range = summary.get("date_range") or {}
            summary_df = pd.DataFrame([{
                "validation_status": summary.get("validation_status", ""),
                "error_count": int(summary.get("error_count", 0)),
                "warning_count": int(summary.get("warning_count", 0)),
                "template": summary.get("template", ""),
                "metric_count": int(summary.get("metric_count", 0)),
                "date_min": date_range.get("min", ""),
                "date_max": date_range.get("max", ""),
            }])
        else:
            summary_df = pd.DataFrame(columns=_REPORT_SUMMARY_COLS)
        _write_df(con, "report_summary", summary_df)
        created.append("report_summary")

        con.execute("""
            CREATE OR REPLACE VIEW v_latest_kpis AS
            SELECT * FROM long_metrics
            WHERE rollup_level = 'date_only'
              AND CAST(date AS VARCHAR) = (
                  SELECT MAX(CAST(date AS VARCHAR))
                  FROM long_metrics
                  WHERE rollup_level = 'date_only'
              )
        """)
        created.append("v_latest_kpis")

        con.execute("""
            CREATE OR REPLACE VIEW v_metric_trends AS
            SELECT * FROM long_metrics
            WHERE rollup_level = 'date_only'
            ORDER BY metric_id, date
        """)
        created.append("v_metric_trends")

        con.execute("""
            CREATE OR REPLACE VIEW v_report_insights AS
            SELECT * FROM report_insights
        """)
        created.append("v_report_insights")

    finally:
        con.close()

    return created


def _ensure_cols(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if df.empty and len(df.columns) == 0:
        return pd.DataFrame(columns=columns)
    return df


def _write_df(con: duckdb.DuckDBPyConnection, table_name: str, df: pd.DataFrame) -> None:
    if len(df.columns) == 0:
        con.execute(f"CREATE OR REPLACE TABLE {table_name} (placeholder VARCHAR)")
        return
    view_name = f"_src_{table_name}"
    con.register(view_name, df)
    con.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM {view_name}")
