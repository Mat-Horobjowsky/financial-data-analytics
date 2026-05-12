# report_engine v1.4

Generates `report.md`, `report.html`, `summary.json`, and `insights.json` from a Metrics Engine output directory. Supports built-in report templates to control which sections are included. Optionally generates `report.pdf` from the rendered HTML.

## Usage

```bash
report-engine build --input <metrics_output_dir> --output <output_dir>
```

With a template:

```bash
report-engine build \
  --input "../metrics_engine/outputs/time_test" \
  --output outputs/report_v12 \
  --template executive_summary
```

With PDF export:

```bash
report-engine build \
  --input "../metrics_engine/outputs/time_test" \
  --output outputs/report_v12 \
  --pdf
```

## Templates

The `--template` flag selects which sections appear in `report.md` and `report.html`. Default is `full_report`.

| Template | Sections included |
|---|---|
| `full_report` (default) | Header, Validation, KPI Snapshot, Key Insights, Metrics Summary, Metric Dictionary |
| `executive_summary` | Header, Validation, KPI Snapshot, Key Insights |
| `metrics_detail` | Header, Validation, Metrics Summary, Metric Dictionary |
| `readiness_summary` | Header, Validation, Readiness Snapshot, Open Gaps, Critical Items, Readiness by Segment, Recommended Next Steps, Metric Dictionary |

`summary.json` and `insights.json` are always written regardless of selected template.

The selected template name is recorded in `summary.json` under the `"template"` key.

### readiness_summary

Designed for readiness-specific Metrics Engine output. Detects the following metric IDs and renders client-facing readiness language:

| Metric ID | Label |
|---|---|
| `readiness_completion_pct` | Readiness Completion % |
| `open_gap_count` | Open Gaps |
| `critical_item_count` | Critical Items |
| `total_requirement_count` | Total Requirements |

Falls back gracefully if these metrics are not present. Renders segment breakdowns (By Category, By Market) when `date_category` or `date_market` rollup rows are available in `long_metrics.csv`.

**Recommended Next Steps** generates deterministic, prioritised recommendations from the available readiness data. Rules applied in order:

1. If `critical_item_count > 0` — escalate critical blockers (severity: critical).
2. Category with the highest `open_gap_count` — category-specific gap recommendation (severity: high).
3. Category with the lowest `readiness_completion_pct` — category-specific completion recommendation (severity: high).
4. If overall `readiness_completion_pct < 60%` — recommend holding transaction / RFP outreach (severity: medium).
5. If overall `readiness_completion_pct ≥ 80%` and `critical_item_count == 0` — recommend preparing market-facing materials (severity: low).

Known categories with tailored recommendation text: `power`, `fiber`, `permitting`, `site_control`, `commercial`, `capital`. Unknown categories use a generic fallback. The recommendation logic lives in `report_engine/insights.py` (`build_readiness_recommendations`) and is shared by both the Markdown and HTML renderers.

Example:

```bash
report-engine build \
  --input "../metrics_engine/outputs/readiness" \
  --output outputs/readiness_report \
  --template readiness_summary
```

## Input files

| File | Required | Description |
|---|---|---|
| `validation_report.json` | Yes | Validation status, errors, and warnings |
| `long_metrics.csv` | No | Metrics in long format (one row per metric per date) |
| `wide_metrics.csv` | No | Metrics in wide format (carried for future use, not rendered) |
| `metric_dictionary.csv` | No | Metric definitions (id, label, type, unit, description) |

## Output files

| File | Description |
|---|---|
| `report.md` | Markdown report with selected template sections |
| `report.html` | Self-contained HTML report with inline CSS |
| `summary.json` | Machine-readable summary: validation status, metric count, date range, rollup levels, template name |
| `insights.json` | Deterministic period-over-period insight records (one per metric with valid change data) |
| `report.pdf` | PDF export of `report.html` — only created when `--pdf` is passed |

### PDF dependency and Python version compatibility

PDF generation uses `xhtml2pdf`, declared as the `pdf` optional extra.

```bash
pip install xhtml2pdf
# or
pip install "report_engine[pdf]"
```

PDF generation has been validated on Python 3.12. If `xhtml2pdf` is not installed or is unavailable in your environment, PDF output is skipped and an informational message is printed; all other outputs are unaffected.

## Report sections

### KPI Snapshot

Shows the latest available value for each metric — one row per metric, most recent period only. Omitted when no metrics data is available.

### Key Insights

Deterministic, data-grounded bullet points derived from period-over-period change. Each insight names the metric, states whether it increased, decreased, or remained flat, and includes the formatted change percentage. Section is omitted when no period-over-period columns are present or all change values are null.

### Metrics Summary

Full long-format metrics table sorted by date then metric ID. Displays formatted values (currency, percent, comma-separated integers). When `prior_period_value`, `period_change`, and `period_change_pct` columns are present in the input, they appear as additional columns (Prior Period, Change, Change %).

### Metric Dictionary

Definitions table from `metric_dictionary.csv`. Column headers are rendered in client-friendly form:

| Raw column | Display header |
|---|---|
| `id` | Metric ID |
| `label` | Metric |
| `type` | Type |
| `unit` | Unit |
| `description` | Description |

### Validation

Validation status, errors, and warnings sourced from `validation_report.json`.

## Development

```bash
pip install -e ".[dev]"
pytest
```
