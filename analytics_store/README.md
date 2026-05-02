# analytics_store v0.1

DuckDB-backed analytics store for Metrics Engine and Report Engine outputs.

Loads trusted metric outputs and report artifacts into a queryable DuckDB database ready for Power BI, visual layers, or future analytics layers.

## Setup

All three engines must be installed first, then:

```bash
cd analytics_store
pip install -e ".[dev]"
```

## CLI

```bash
analytics-store build \
  --metrics <metrics_output_dir> \
  --report <report_output_dir> \
  --output outputs/store.duckdb
```

`--report` is optional. If omitted, `report_insights` and `report_summary` tables are created empty.

## CLI Flags

| Flag | Default | Description |
|---|---|---|
| `--metrics` | *(required)* | Metrics Engine output directory |
| `--report` | *(none)* | Report Engine output directory (optional) |
| `--output` | `outputs/store.duckdb` | Output DuckDB file path |

## Output: Tables

| Table | Source | Description |
|---|---|---|
| `long_metrics` | `long_metrics.csv` | One row per metric per rollup level |
| `wide_metrics` | `wide_metrics.csv` | One row per date+segment with metrics as columns |
| `metric_dictionary` | `metric_dictionary.csv` | Metric definitions, units, and descriptions |
| `metrics_validation_summary` | `validation_report.json` | Validation status, error count, warning count |
| `report_insights` | `insights.json` | Period-over-period insight records (empty if no report) |
| `report_summary` | `summary.json` | Report metadata: template, date range, metric count (empty if no report) |

## Output: Views

| View | Description |
|---|---|
| `v_latest_kpis` | Most recent value per metric (date_only rollup, latest date only) |
| `v_metric_trends` | All date_only rows ordered by metric and date |
| `v_report_insights` | All rows from report_insights |

## Example Run Against Demo Outputs

```bash
cd analytics_store
analytics-store build \
  --metrics ../metrics_engine/outputs/demo \
  --report ../report_engine/outputs/demo_full_report \
  --output outputs/store.duckdb
```

Expected output:

```
Store written to: ...\analytics_store\outputs\store.duckdb
  Tables (6): long_metrics, wide_metrics, metric_dictionary, metrics_validation_summary, report_insights, report_summary
  Views  (3): v_latest_kpis, v_metric_trends, v_report_insights
```

## Architecture

| Module | Role |
|---|---|
| `loader.py` | Reads CSV/JSON files from metrics and report directories into dataclasses |
| `writer.py` | Writes dataclasses to DuckDB tables and creates views |
| `cli.py` | `analytics-store build` CLI entry point |

## Current Limitations

- `metrics_output.xlsx` is intentionally ignored; CSV/JSON outputs are canonical.
- `wide_metrics` column schema is dynamic; no fixed schema is enforced on that table.
- No Power BI integration, GUI, or API — intended as a direct `.duckdb` file for downstream tools.
