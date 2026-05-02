# Financial Data Analytics

A modular analytics engineering portfolio focused on turning raw data into decision-ready intelligence.

This repository documents my progression from analyst workflows to reusable analytics systems — combining data ingestion, metric governance, reporting automation, and AI-assisted development workflows.

The core principle:

```
Clean data → Trusted metrics → Visuals anywhere
```

---

## Active Product Stack

| Engine | Version | Input | Output |
|---|---|---|---|
| **Intake Engine** | v1.x | Raw CSV / XLSX (messy, unstructured) | Clean CSV, HTML quality report, validation JSON, profiling JSON |
| **Metrics Engine** | v1.1 | Clean CSV | Long + wide KPI tables, metric dictionary, validation report, Excel workbook |
| **Report Engine** | v1.2 | Metrics Engine output directory | Markdown + HTML reports, summary JSON, insights JSON |
| **Analytics Pipeline** | v0.1 | Raw CSV / XLSX | All engine outputs + `pipeline_summary.json` |

Each engine is a standalone Python CLI package with tests, documented outputs, and a clearly scoped role in the pipeline.

```
Intake Engine
    ↓
Metrics Engine
    ↓
Report Engine
    ↓
Power BI / Excel / dashboards
```

---

## End-to-End Demo Workflow

The following commands run the full pipeline on the sample data center dataset.

### Sample dataset

**Raw input:** `intake_engine/tests/fixtures/messy_data_center_sample_for_intake.csv`

A realistic messy export: inconsistent headers (`Report Date`, `Total Revenue ($)`, `Geo`, `Vendor`), extra non-metric columns, and formatting in numeric fields. The pipeline cleans, validates, calculates KPIs, and produces client-ready report artifacts.

### Step 1 — Intake Engine

```bash
cd intake_engine
intake run tests/fixtures/messy_data_center_sample_for_intake.csv --profile --validate
cd ..
```

Outputs to `intake_engine/outputs/`:
- `messy_data_center_sample_for_intake_clean.csv` — cleaned, schema-normalized data
- `messy_data_center_sample_for_intake_report.html` — self-contained HTML quality report
- `messy_data_center_sample_for_intake_validation.json` — validation result (PASS / WARN / FAIL)
- `messy_data_center_sample_for_intake_profile.json` — semantic type inference and transformation log

### Step 2 — Metrics Engine (with prior-period analysis)

```bash
cd metrics_engine
metrics-engine run \
  --input ../intake_engine/outputs/messy_data_center_sample_for_intake_clean.csv \
  --output outputs/demo \
  --with-time
cd ..
```

Outputs to `metrics_engine/outputs/demo/`:
- `long_metrics.csv` — one row per metric per rollup level, with `prior_period_value`, `period_change`, and `period_change_pct` columns
- `wide_metrics.csv` — one row per date+segment, metrics as columns
- `metric_dictionary.csv` — definitions, units, and descriptions for all 6 KPIs
- `validation_report.json` — full validation status, errors, and warnings
- `metrics_output.xlsx` — all outputs in a single Excel workbook

### Step 3 — Report Engine, full report

```bash
cd report_engine
report-engine build \
  --input ../metrics_engine/outputs/demo \
  --output outputs/demo_full_report
```

Outputs to `report_engine/outputs/demo_full_report/`:
- `report.md` — full Markdown report with all six sections
- `report.html` — self-contained HTML report with inline CSS
- `summary.json` — machine-readable summary (validation status, metric count, date range, template name)
- `insights.json` — deterministic period-over-period insight records

### Step 4 — Report Engine, executive summary

```bash
report-engine build \
  --input ../metrics_engine/outputs/demo \
  --output outputs/demo_executive_summary \
  --template executive_summary
cd ..
```

Outputs a compact report containing Header, Validation, KPI Snapshot, and Key Insights only — no raw data tables.

---

## Intake Engine

A modular Python CLI ingestion tool that converts messy CSV and XLSX files into clean, analytics-ready outputs.

### Purpose

The Intake Engine solves the first problem in most analytics workflows: messy source files.

It handles delimiter detection, header normalization, numeric and date cleaning, validation, profiling, and HTML quality reports — all from a single command.

### Key Features

- CSV, TSV, and Excel ingestion with auto-detected delimiters
- Header normalization (trim, lowercase, snake_case)
- Numeric normalization — strips `$`, `,`, `%`, parenthetical negatives
- Date normalization — standardizes 12+ date formats to ISO 8601
- Validation — required columns, null rates, duplicate rates, type rules
- Profiling — semantic type inference and transformation tracking
- Self-contained HTML quality reports
- Parquet export
- DuckDB sink (append or replace)
- Batch processing
- YAML-driven pipeline config
- CLI workflow
- Test coverage

### Setup

```bash
cd intake_engine
pip install -e ".[dev]"
```

### CLI

```bash
intake --help
```

---

## Metrics Engine

A config-driven KPI calculation engine that turns cleaned data into validated, reusable metric outputs.

### Purpose

The Metrics Engine creates a trusted semantic layer for business metrics.

Instead of calculating KPIs separately in dashboards, spreadsheets, and reports, metric logic is centralized, tested, and reusable.

### Key Features

- CSV and Excel input
- Schema-driven column normalization
- YAML-based metric definitions
- Validation before calculation
- Configurable segment rollups (date, date+region, date+provider, date+region+provider)
- Sum-before-divide KPI logic (prevents weighted-average distortion)
- Long and wide metric outputs
- Metric dictionary generation
- Validation report export
- Excel workbook export
- Prior-period time analysis (`--with-time`)
- CLI workflow
- Test coverage

### Setup

```bash
cd metrics_engine
pip install -e ".[dev]"
```

### CLI

```bash
metrics-engine --help
```

### Example Outputs

| File | Description |
|---|---|
| `long_metrics.csv` | One row per metric per rollup level |
| `wide_metrics.csv` | One row per date+segment with metrics as columns |
| `metric_dictionary.csv` | Metric definitions, units, and descriptions |
| `validation_report.json` | Validation status, errors, and warnings |
| `metrics_output.xlsx` | All outputs in a single Excel workbook |

---

## Report Engine

A lightweight reporting engine that converts trusted Metrics Engine outputs into client-ready report artifacts.

### Purpose

The Report Engine is the final layer of the stack.

It takes validated metric outputs and turns them into structured deliverables that support client handoff, portfolio demos, executive summaries, and reporting automation.

### Key Features

- Reads Metrics Engine output directory
- Built-in report templates (`full_report`, `executive_summary`, `metrics_detail`)
- `--template` CLI flag to select the report scope
- KPI Snapshot — latest value per metric, most recent period only
- Key Insights — deterministic, data-grounded period-over-period bullets
- Metrics Summary — formatted long-format table with optional period-over-period columns
- Metric Dictionary — client-friendly column headers
- Self-contained HTML report with inline CSS
- Markdown report
- `summary.json` — machine-readable metadata including selected template name
- `insights.json` — structured insight records per metric
- CLI workflow
- Test coverage

### Setup

```bash
cd report_engine
pip install -e ".[dev]"
```

### CLI

```bash
report-engine build --input <metrics_output_dir> --output <output_dir> [--template full_report|executive_summary|metrics_detail]
```

### Templates

| Template | Sections |
|---|---|
| `full_report` (default) | Header, Validation, KPI Snapshot, Key Insights, Metrics Summary, Metric Dictionary |
| `executive_summary` | Header, Validation, KPI Snapshot, Key Insights |
| `metrics_detail` | Header, Validation, Metrics Summary, Metric Dictionary |

`summary.json` and `insights.json` are always written regardless of selected template.

### Example Outputs

| File | Description |
|---|---|
| `report.md` | Markdown report with selected template sections |
| `report.html` | Self-contained HTML report with inline CSS |
| `summary.json` | Machine-readable summary: status, metric count, date range, template name |
| `insights.json` | Deterministic period-over-period insight records |

---

## Analytics Pipeline

A stage-based orchestrator that runs all three engines in sequence from a single command.

### Purpose

The Analytics Pipeline removes the need to run Intake, Metrics, and Report as separate steps. One command drives the full workflow, stops at the first failed stage, and produces a `pipeline_summary.json` recording the status and output files for every stage.

### Setup

All three engines must be installed first:

```bash
cd intake_engine && pip install -e . && cd ..
cd metrics_engine && pip install -e . && cd ..
cd report_engine && pip install -e . && cd ..
cd analytics_pipeline && pip install -e ".[dev]"
```

### CLI

```bash
analytics-pipeline run \
  --input <raw_input.csv> \
  --output outputs/demo \
  --with-time \
  --template full_report
```

| Flag | Default | Description |
|---|---|---|
| `--input` | *(required)* | Raw input file (CSV or XLSX) |
| `--output` | `outputs/pipeline` | Pipeline output root directory |
| `--with-time` | off | Enable prior-period time analysis in Metrics Engine |
| `--template` | `full_report` | Report template (`full_report`, `executive_summary`, `metrics_detail`) |

### Output Structure

```
<output>/
├── intake/     # Clean CSV, HTML quality report, validation JSON
├── metrics/    # Long/wide metrics, metric dictionary, validation report, Excel workbook
├── report/     # report.html, report.md, summary.json, insights.json
└── pipeline_summary.json
```

---

## AI Workflows

The `ai_workflows/` folder contains reusable workflow instructions for AI coding assistants.

These workflows keep development consistent, modular, and scoped to the active engine stack.

| Skill | Purpose |
|---|---|
| `repo_inspection` | Inspect repo state before making changes |
| `intake_feature_build` | Build or modify Intake Engine features |
| `metrics_feature_build` | Build or modify Metrics Engine features |
| `report_feature_build` | Build or modify Report Engine features |
| `testing_and_validation` | Validate work before declaring complete |
| `documentation_update` | Keep docs accurate and portfolio-ready |
| `scope_discipline` | Prevent overbuilding and premature architecture |

---

## Archive

The `archive/` folder contains earlier Excel and SQL projects.

These are preserved for portfolio history and learning progression but are not part of the active engine stack.

Active development is focused on `intake_engine/`, `metrics_engine/`, `report_engine/`, and `ai_workflows/`.

---

## Roadmap

### Completed

- **Intake Engine** — ingest and clean messy CSV / XLSX files; validate, profile, and export clean analytics-ready data
- **Metrics Engine v1.1** — YAML-driven KPI calculation across configurable rollup levels; prior-period time analysis with `--with-time`
- **Report Engine v1.2** — client-ready Markdown and HTML reports; KPI Snapshot; deterministic Key Insights; three built-in templates (`full_report`, `executive_summary`, `metrics_detail`); `insights.json`
- **Analytics Pipeline v0.1** — single-command orchestrator running all three engines in sequence; stops on first failure; writes `pipeline_summary.json`
- **End-to-End Pipeline** — full Intake → Metrics → Report workflow running on a shared sample dataset

### Next Priorities

**Visual Layer** — reusable Power BI dashboards or lightweight Python charts that consume trusted Metrics Engine outputs directly

**PDF Export** — optional PDF generation from Report Engine's existing HTML output, for direct client delivery

---

## Skills Demonstrated

- Python analytics engineering
- Data ingestion and cleaning automation
- Schema normalization
- KPI and metric layer design
- Report automation
- SQL data modeling
- Power BI reporting
- DuckDB workflows
- YAML-driven configuration
- Data quality validation
- Modular system architecture
- Test-driven development
- CLI tool design
- Git and GitHub workflow
- AI-assisted software development workflows

---

## Connect

LinkedIn: www.linkedin.com/in/mat-horobjowsky
