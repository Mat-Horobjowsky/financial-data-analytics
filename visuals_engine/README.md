# Visuals Engine

Renders trusted metrics from `analytics.duckdb` into static, self-contained HTML dashboards.

Sits downstream of Analytics Store in the pipeline:

```
Metrics Engine → Analytics Store → Visuals Engine → readiness_dashboard.html
```

## Prerequisites

`analytics.duckdb` must already exist and contain populated `long_metrics`, `metric_dictionary`, and `metrics_validation_summary` tables. These are produced by running the Metrics Engine followed by the Analytics Store.

## CLI Usage

```bash
visuals-engine build \
  --store outputs/readiness/analytics.duckdb \
  --spec visuals_engine/visuals_engine/specs/readiness_dashboard.yaml \
  --output outputs/visuals/readiness
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--store` | Yes | Path to `analytics.duckdb` |
| `--spec`  | Yes | Path to dashboard spec YAML |
| `--output`| Yes | Output directory (created if it does not exist) |

## Example Output

```
outputs/visuals/readiness/
  readiness_dashboard.html    ← open in any browser, no internet required
  visuals_summary.json        ← machine-readable summary of what was rendered
```

`visuals_summary.json` example:

```json
{
  "dashboard": "Project Readiness Dashboard",
  "metrics_rendered": ["critical_item_count", "open_gap_count", "readiness_completion_pct", "total_requirement_count"],
  "sections_rendered": ["kpi_cards", "category_breakdown", "market_breakdown"],
  "sections_skipped": [],
  "validation_status": "passed_with_warnings",
  "generated_at": "2026-05-08T10:30:00+00:00"
}
```

## Dashboard Sections

| Section | Data source | Skipped when |
|---------|-------------|--------------|
| KPI Cards | `long_metrics` WHERE `rollup_level = 'date_only'` | Required |
| Category Breakdown | `long_metrics` WHERE `rollup_level = 'date_category'` | No category rows in store |
| Market Breakdown | `long_metrics` WHERE `rollup_level = 'date_market'` | No market rows in store |

Optional breakdown sections are skipped gracefully and recorded in `visuals_summary.json`.

## Spec File

The dashboard spec YAML (`specs/readiness_dashboard.yaml`) controls:

- Dashboard title and description
- Which metrics appear in KPI cards (by `metric_id`)
- Which breakdown rollup levels to query
- Which tables to read from the store
- Whether breakdown sections are optional

To create a different dashboard, write a new spec file and pass it with `--spec`.

## Module Layout

```
visuals_engine/
  cli.py        argument parsing, writes HTML + JSON to --output
  loader.py     DuckDB queries; returns plain Python dicts
  renderer.py   transforms loaded data into Jinja2 context; renders HTML + JSON
  templates/
    readiness_dashboard.html   Jinja2 template (self-contained CSS, no CDN)
  specs/
    readiness_dashboard.yaml   dashboard definition
```

## Installing and Running Tests

```bash
cd visuals_engine
pip install -e ".[dev]"
pytest
```

## Known Limitations

- Charts are CSS progress bars — no interactivity. Interactive charts (Chart.js) are deferred to v0.2.
- Only one template is supported: `readiness_dashboard.html`. Multiple templates are deferred.
- Pipeline integration (`analytics-pipeline run`) is not yet wired. Run `visuals-engine build` directly after `analytics-store build`.

## Upstream Integration

This module reads from `analytics.duckdb`. To produce a populated store:

```bash
# 1. Run Metrics Engine
cd metrics_engine
metrics-engine run --input data/sample_readiness.csv --config config/readiness_schema.yaml --metrics config/readiness_metrics.yaml --output ../outputs/readiness

# 2. Build Analytics Store
cd ../analytics_store
analytics-store build --metrics ../outputs/readiness --output ../outputs/readiness/analytics.duckdb

# 3. Build Dashboard
cd ../visuals_engine
visuals-engine build --store ../outputs/readiness/analytics.duckdb --spec visuals_engine/specs/readiness_dashboard.yaml --output ../outputs/visuals/readiness
```
