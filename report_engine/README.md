# report_engine

Generates `report.md`, `report.html`, and `summary.json` from a Metrics Engine output directory.

## Usage

```bash
py -m report_engine.cli build --input <metrics_output_dir> --output <output_dir>
```

Example:

```bash
py -m report_engine.cli build \
  --input "../metrics_engine/outputs/intake_test" \
  --output outputs/report_test
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
| `report.md` | Markdown report with Validation, Metrics Summary, and Metric Dictionary sections |
| `report.html` | Self-contained HTML report with inline CSS |
| `summary.json` | Machine-readable summary: validation status, metric count, date range, rollup levels |

## Development

```bash
pip install -r requirements.txt
py -m pytest tests/ -v
```
