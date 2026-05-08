# analytics_pipeline v0.2

Stage-based orchestrator for the Intake → Metrics → Report → Store pipeline.

Runs the core three engines in sequence from a single command, with an optional Analytics Store stage (`--with-store`). Stops at the first failed stage and writes a `pipeline_summary.json` recording the status, command, and generated files for every stage.

## Usage

```bash
cd analytics_pipeline

# Core pipeline (Intake → Metrics → Report)
analytics-pipeline run \
  --input ../intake_engine/tests/fixtures/messy_data_center_sample_for_intake.csv \
  --output outputs/demo \
  --with-time \
  --template full_report

# With Analytics Store stage
analytics-pipeline run \
  --input ../intake_engine/tests/fixtures/messy_data_center_sample_for_intake.csv \
  --output outputs/demo \
  --with-time \
  --template full_report \
  --with-store
```

## CLI flags

| Flag | Default | Description |
|---|---|---|
| `--input` | *(required)* | Raw input file (CSV or XLSX) |
| `--output` | `outputs/pipeline` | Pipeline output root directory |
| `--with-time` | off | Enable prior-period time analysis in Metrics Engine |
| `--template` | `full_report` | Report template (`full_report`, `executive_summary`, `metrics_detail`) |
| `--with-store` | off | Run Analytics Store stage after report; creates `store/analytics.duckdb` |
| `--with-visuals` | off | Run Visuals Engine after store; creates `visuals/readiness_dashboard.html`; implies `--with-store` |
| `--metrics-config` | `metrics_engine/config/metrics.yaml` | Custom Metrics Engine config YAML (enables alternate metric packs) |
| `--schema-config` | `metrics_engine/config/schema.yaml` | Custom Metrics Engine schema YAML |

## Usage examples

### Data center KPIs (default)

```bash
analytics-pipeline run \
  --input data/sample_data_centers.csv \
  --output outputs/pipeline \
  --with-time \
  --template full_report \
  --with-store
```

### Readiness metrics pack

Pass `--metrics-config` and `--schema-config` to run any alternate metric pack. The pipeline does not hardcode readiness — the flags are generic.

```bash
analytics-pipeline run \
  --input metrics_engine/data/sample_readiness.csv \
  --output outputs/pipeline_readiness \
  --metrics-config metrics_engine/config/readiness_metrics.yaml \
  --schema-config metrics_engine/config/readiness_schema.yaml \
  --with-visuals
```

Produces `outputs/pipeline_readiness/visuals/readiness_dashboard.html`.

## Output structure

```
<pipeline_output>/
├── intake/          # Intake Engine outputs (clean CSV, validation JSON, ...)
├── metrics/         # Metrics Engine outputs (long/wide metrics, metric dictionary, ...)
├── report/          # Report Engine outputs (report.html, report.md, insights.json, ...)
├── store/           # Analytics Store output — only created when --with-store is passed
│   └── analytics.duckdb
├── visuals/         # Visuals Engine output — only created when --with-visuals is passed
│   ├── readiness_dashboard.html
│   └── visuals_summary.json
└── pipeline_summary.json
```

### pipeline_summary.json

Without `--with-store`:

```json
{
  "pipeline_version": "0.2.0",
  "generated_at": "...",
  "input_path": "...",
  "output_dir": "...",
  "with_time": true,
  "with_store": false,
  "template": "full_report",
  "status": "success",
  "stages": {
    "intake":  {"status": "success", "command": "...", "output_dir": "...", "generated_files": [...]},
    "metrics": {"status": "success", "command": "...", "output_dir": "...", "generated_files": [...]},
    "report":  {"status": "success", "command": "...", "output_dir": "...", "generated_files": [...], "template": "full_report"}
  },
  "future_stages": ["store"]
}
```

With `--with-store`:

```json
{
  "pipeline_version": "0.2.0",
  "with_time": true,
  "with_store": true,
  "template": "full_report",
  "status": "success",
  "stages": {
    "intake":  {"status": "success", ...},
    "metrics": {"status": "success", ...},
    "report":  {"status": "success", ..., "template": "full_report"},
    "store":   {"status": "success", "output_dir": ".../store", "generated_files": ["analytics.duckdb"], "output_path": ".../store/analytics.duckdb"}
  },
  "future_stages": []
}
```

## Prerequisites

The three core engines must be installed before running the pipeline. If you intend to use `--with-store`, install `analytics_store` as well:

```bash
cd intake_engine && pip install -e . && cd ..
cd metrics_engine && pip install -e . && cd ..
cd report_engine && pip install -e . && cd ..
cd analytics_store && pip install -e . && cd ..   # only needed for --with-store
cd analytics_pipeline && pip install -e . && cd ..
```

## Setup

```bash
cd analytics_pipeline
pip install -e ".[dev]"
pytest
```

## Pipeline stages

```
Intake Engine       (always)
    ↓
Metrics Engine      (always — uses --metrics-config / --schema-config if provided)
    ↓
Report Engine       (always)
    ↓
Analytics Store     (optional — enabled with --with-store or implied by --with-visuals)
    ↓
Visuals Engine      (optional — enabled with --with-visuals)
```

Each stage runs only after the previous one succeeds. If any stage fails, later stages are skipped.

## Internal architecture

| Module | Role |
|---|---|
| `stages.py` | Stage definitions — `StageContext`, `StageResult`, command builders, `ACTIVE_STAGES` |
| `runner.py` | Executes stages sequentially, stops on first failure; runs optional store stage |
| `summary.py` | Builds and writes `pipeline_summary.json` |
| `cli.py` | `analytics-pipeline run` entry point |
