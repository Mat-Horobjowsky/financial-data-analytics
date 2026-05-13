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
| `--template` | `full_report` | Report template (`full_report`, `executive_summary`, `metrics_detail`, `readiness_summary`) |
| `--pdf` | off | Generate `report/report.pdf` from the Report Engine output (requires `report_engine[pdf]`) |
| `--report-title` | *(none)* | Title forwarded to Report Engine `--title`; used as the PDF header. Recommended with `--template readiness_summary --pdf`. Defaults to the input folder name when omitted. |
| `--with-store` | off | Run Analytics Store stage after report; creates `store/analytics.duckdb` |
| `--with-visuals` | off | Run Visuals Engine after store; creates `visuals/readiness_dashboard.html`; implies `--with-store` |
| `--with-powerbi-export` | off | Run Power BI CSV export after store; creates `powerbi/*.csv`; implies `--with-store` |
| `--metrics-config` | `metrics_engine/config/metrics.yaml` | Custom Metrics Engine config YAML (enables alternate metric packs) |
| `--schema-config` | `metrics_engine/config/schema.yaml` | Custom Metrics Engine schema YAML |
| `--sheet` | *(none)* | Excel sheet name passed to Intake Engine (optional, for XLSX files with multiple sheets) |
| `--client-context` | *(none)* | Path to `client_context.csv`; injects client name, project name, and project ID into the Visuals Engine dashboard header when `--with-visuals` is used, and copies the file into `powerbi/` when `--with-powerbi-export` is used |

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
  --output outputs/demo_readiness \
  --metrics-config metrics_engine/config/readiness_metrics.yaml \
  --schema-config metrics_engine/config/readiness_schema.yaml \
  --with-visuals
```

Produces `outputs/demo_readiness/visuals/readiness_dashboard.html`.

### Readiness demo from Excel workbook

The readiness workflow begins with a pre-processing step that resolves requirement
statuses from the intake workbook before the pipeline runs.

**Step 1 — Build demo workbook and client context** (requires `readiness_workbook` installed):

```bash
readiness-workbook build \
  --workbook examples/readiness_demo/client_intake_template.xlsx \
  --output examples/readiness_demo/client_intake_template_demo.xlsx \
  --client-context-output examples/readiness_demo/client_context.csv \
  --demo-context
```

**Step 2 — Run the full pipeline** using `--sheet` to select the populated sheet:

```bash
analytics-pipeline run \
  --input examples/readiness_demo/client_intake_template_demo.xlsx \
  --sheet PowerBI_Export \
  --output outputs/demo_readiness_client \
  --metrics-config metrics_engine/config/readiness_metrics.yaml \
  --schema-config metrics_engine/config/readiness_schema.yaml \
  --template readiness_summary \
  --pdf \
  --report-title "Demo AI Infrastructure Co." \
  --with-visuals \
  --with-powerbi-export \
  --client-context examples/readiness_demo/client_context.csv
```

Produces `outputs/demo_readiness_client/report/report.pdf` (polished one-page landscape readiness executive report) and `report.html` (polished client-facing readiness page: dark header, KPI cards, Executive Assessment, Recommended Next Steps, segment tables — no generic Validation block or Metric Dictionary), `outputs/demo_readiness_client/visuals/readiness_dashboard.html` (with client/project identity injected in the header from `--client-context`), and `outputs/demo_readiness_client/powerbi/*.csv`.

## Output structure

```
<pipeline_output>/
├── intake/          # Intake Engine outputs (clean CSV, validation JSON, ...)
├── metrics/         # Metrics Engine outputs (long/wide metrics, metric dictionary, ...)
├── report/          # Report Engine outputs (report.html, report.md, insights.json, ...)
│   └── report.pdf   # optional — only created when --pdf is passed
├── store/           # Analytics Store output — only created when --with-store is passed
│   └── analytics.duckdb
├── visuals/         # Visuals Engine output — only created when --with-visuals is passed
│   ├── readiness_dashboard.html
│   └── visuals_summary.json
├── powerbi/         # Power BI CSV export — only created when --with-powerbi-export is passed
│   ├── readiness_kpis.csv
│   ├── readiness_by_category.csv
│   ├── readiness_by_market.csv
│   ├── validation_summary.csv
│   ├── metric_dictionary.csv
│   └── client_context.csv          # optional — copied when --client-context is provided
├── pipeline_summary.json
└── artifact_manifest.json          # only created on full success; requires no extra flags
```

The CSV schema for the `powerbi/` output is a stable downstream contract. Column names, file names, grain, and data types must not change without updating `docs/powerbi_export_contract.md` and the contract validation tests in `tests/analytics_pipeline/test_powerbi_export_contract.py`.

### pipeline_summary.json

`pipeline_summary.json` records all inputs and resolved config paths so any run can be audited or replayed exactly. When `--client-context` is provided, a `client` block with `client_name`, `project_name`, and `project_id` is included.

```json
{
  "pipeline_version": "0.2.0",
  "generated_at": "...",
  "input_path": "examples/readiness_demo/client_intake_template.xlsx",
  "sheet": "PowerBI_Export",
  "output_dir": "outputs/demo_readiness_client",
  "with_time": false,
  "with_store": true,
  "with_visuals": true,
  "with_powerbi_export": true,
  "with_pdf": true,
  "report_title": "Demo AI Infrastructure Co.",
  "metrics_config_path": "/abs/path/to/metrics_engine/config/readiness_metrics.yaml",
  "schema_config_path": "/abs/path/to/metrics_engine/config/readiness_schema.yaml",
  "client_context_path": "examples/readiness_demo/client_context.csv",
  "client": {
    "client_name": "Demo AI Infrastructure Co.",
    "project_name": "Midwest AI Campus Requirement",
    "project_id": "DEMO-READY-001"
  },
  "template": "readiness_summary",
  "status": "success",
  "stages": {
    "intake":        {"status": "success", "command": "...", "output_dir": "...", "generated_files": [...]},
    "metrics":       {"status": "success", ...},
    "report":        {"status": "success", ..., "template": "full_report"},
    "store":         {"status": "success", ..., "output_path": ".../store/analytics.duckdb"},
    "visuals":       {"status": "success", ...},
    "powerbi_export":{"status": "success", ...}
  },
  "future_stages": []
}
```

`metrics_config_path` and `schema_config_path` are always absolute paths — either the resolved custom path or the engine's built-in default.

### artifact_manifest.json

`artifact_manifest.json` is written alongside `pipeline_summary.json` after every successful full pipeline run. It classifies every generated file into three audiences — `client_facing`, `bi_facing`, and `internal` — so a reviewer, automation step, or future packaging workflow can identify deliverables without parsing the full output tree.

```json
{
  "manifest_version": "1.0",
  "generated_at": "...",
  "pipeline_version": "0.2.0",
  "client": {
    "client_name": "Demo AI Infrastructure Co.",
    "project_name": "Midwest AI Campus Requirement",
    "project_id": "DEMO-READY-001"
  },
  "run": {
    "status": "success",
    "input_file": "...",
    "template": "readiness_summary",
    "output_dir": "outputs/demo_readiness_client"
  },
  "artifacts": [
    {
      "name": "Executive Report (HTML)",
      "category": "report",
      "audience": "client_facing",
      "relative_path": "report/report.html",
      "description": "Client-facing executive summary report (HTML)",
      "source_stage": "report",
      "generated_at": "..."
    },
    ...
  ]
}
```

Artifact audiences:

| Audience | Files |
|---|---|
| `client_facing` | `report/report.html`, `report/report.pdf`, `visuals/readiness_dashboard.html`, `visuals/readiness_dashboard.pdf` |
| `bi_facing` | all files under `powerbi/` |
| `internal` | all other files — intake outputs, metrics tables, analytics store, metadata JSONs |

Unrecognised files (category `unknown`) are included with audience `internal` rather than silently omitted. The `client` block is populated from `--client-context` when provided; it is `null` when no context is passed.

## Prerequisites

All engines are local editable packages — they cannot be declared as PyPI dependencies. Install the ones you need before running the pipeline:

```bash
# Always required
pip install -e intake_engine
pip install -e metrics_engine
pip install -e report_engine

# Required for --with-store (also implied by --with-visuals and --with-powerbi-export)
pip install -e analytics_store

# Required for --with-visuals and/or --with-powerbi-export
pip install -e visuals_engine

# Install the pipeline itself
pip install -e analytics_pipeline
```

To install everything at once from the repo root:

```bash
pip install -e intake_engine -e metrics_engine -e report_engine -e analytics_store -e visuals_engine -e readiness_workbook -e analytics_pipeline
```

## Setup

From the **repo root**, install the pipeline and all engines into your active environment:

```bash
pip install -e "analytics_pipeline[dev]"
```

This installs `analytics_pipeline` plus all five engine packages (declared as local path dependencies under `[dev]`) and `pytest`. After that, run the test suite from the repo root:

```bash
py -m pytest analytics_pipeline/tests/
```

Expected: **214 passed, 1 skipped** (the env-gated integration test is skipped by default).

To run the end-to-end readiness integration test (slower, requires all engines installed):

```bash
$env:ANALYTICS_PIPELINE_INTEGRATION_TESTS="1"   # PowerShell
py -m pytest analytics_pipeline/tests/analytics_pipeline/test_integration_readiness.py -v
```

## Pipeline stages

```
Intake Engine        (always)
    ↓
Metrics Engine       (always — uses --metrics-config / --schema-config if provided)
    ↓
Report Engine        (always)
    ↓
Analytics Store      (optional — enabled with --with-store or implied by --with-visuals / --with-powerbi-export)
    ↓
Visuals Engine       (optional — enabled with --with-visuals)
    ↓
Power BI Export      (optional — enabled with --with-powerbi-export; independent of --with-visuals)
```

Each stage runs only after the previous one succeeds. If any stage fails, later stages are skipped.

## Internal architecture

| Module | Role |
|---|---|
| `stages.py` | Stage definitions — `StageContext`, `StageResult`, command builders, `ACTIVE_STAGES` |
| `runner.py` | Executes stages sequentially, stops on first failure; runs optional store stage |
| `summary.py` | Builds and writes `pipeline_summary.json` |
| `cli.py` | `analytics-pipeline run` entry point |
