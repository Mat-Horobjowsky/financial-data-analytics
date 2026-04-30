# Financial Data Analytics

A modular analytics engineering portfolio focused on turning raw data into decision-ready intelligence.

This repository documents my progression from analyst workflows to reusable analytics systems — combining data ingestion, metric governance, reporting automation, BI workflows, and AI-ready data foundations.

The core principle behind this repo is:

```
Clean data → Trusted metrics → Visuals anywhere
```

---

## Repository Structure

```
financial-data-analytics/
├── intake_engine/        # Raw/messy data → clean analytics-ready data
├── metrics_engine/       # Clean data → trusted reusable KPI outputs
├── report_engine/        # Trusted metrics → client-ready reports
├── ai_workflows/         # Reusable AI workflow instructions for coding assistants
├── archive/              # Historical Excel, SQL, and learning projects
├── CLAUDE.md             # Repo-level AI coding assistant guidance
└── README.md
```

---

## Active Product Stack

This repo is organized around a three-engine analytics workflow:

```
Intake Engine
    ↓
Metrics Engine
    ↓
Report Engine
```

Each engine is a standalone Python CLI package with tests, documented outputs, and a clear role in the pipeline.

---

## Intake Engine

A modular Python CLI ingestion tool that converts messy CSV, TSV, and Excel files into clean, analytics-ready outputs.

### Purpose

The Intake Engine solves the first problem in most analytics workflows: messy source files.

It helps standardize raw data before it reaches dashboards, metric layers, reports, or downstream analysis.

### Key Features

- CSV, TSV, and Excel ingestion
- Delimiter auto-detection
- Multi-sheet Excel support
- Data cleaning and normalization
- Validation and profiling
- HTML quality reports
- DuckDB loading and append mode
- YAML-based configuration
- Batch processing
- CLI workflow
- Test coverage

### Setup

```bash
cd intake_engine
pip install -e .
```

For development (includes test runner):

```bash
pip install -e ".[dev]"
```

### CLI

```bash
intake --help
```

---

## Metrics Engine

A config-driven KPI calculation engine that turns cleaned data into validated, reusable metric outputs for Power BI, Excel, reporting tools, and future AI analytics workflows.

### Purpose

The Metrics Engine creates a trusted semantic layer for business metrics.

Instead of calculating KPIs separately in dashboards, spreadsheets, and reports, metric logic is centralized, tested, and reusable.

### Key Features

- CSV and Excel input
- Schema-driven column normalization
- YAML-based metric definitions
- Validation before calculation
- Configurable segment rollups
- Sum-before-divide KPI logic
- Long and wide metric outputs
- Metric dictionary generation
- Validation report export
- Prior-period time analysis
- CLI workflow
- Test coverage

### Setup

```bash
cd metrics_engine
pip install -e .
```

For development (includes test runner):

```bash
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

The Report Engine is the reporting layer of the stack.

It takes validated metric outputs and turns them into structured deliverables that can support client handoff, portfolio demos, executive summaries, and future reporting automation.

### Key Features

- Reads Metrics Engine outputs
- Generates Markdown and HTML reports
- Produces a machine-readable summary JSON
- Keeps reporting logic separate from metric logic
- CLI workflow
- Test coverage

### Setup

```bash
cd report_engine
pip install -e .
```

For development (includes test runner):

```bash
pip install -e ".[dev]"
```

### CLI

```bash
report-engine --help
```

### Example Outputs

| File | Description |
|---|---|
| `report.md` | Markdown report with validation, metrics summary, and metric dictionary |
| `report.html` | Self-contained HTML report with inline CSS |
| `summary.json` | Machine-readable summary: status, metric count, date range |

---

## End-to-End Workflow

```
Raw CSV / Excel files
        ↓
  Intake Engine          (raw → clean)
        ↓
Cleaned analytics-ready data
        ↓
  Metrics Engine         (clean → trusted KPIs)
        ↓
Trusted KPI outputs
        ↓
  Report Engine          (metrics → client artifacts)
        ↓
Client-ready report artifacts
        ↓
Power BI / Excel / dashboards / AI analytics workflows
```

---

## AI Workflows

The `ai_workflows/` folder contains reusable workflow instructions for AI coding assistants.

These workflows help keep future development consistent, modular, and scoped.

Current workflow skills:

| Skill | Purpose |
|---|---|
| `repo_inspection` | Inspect repo state before making changes |
| `intake_feature_build` | Build or modify Intake Engine features |
| `metrics_feature_build` | Build or modify Metrics Engine features |
| `report_feature_build` | Build or modify Report Engine features |
| `testing_and_validation` | Validate work before declaring complete |
| `documentation_update` | Keep docs accurate and portfolio-ready |
| `scope_discipline` | Prevent overbuilding and premature architecture |

These are used alongside `CLAUDE.md` to guide development and reduce repeated prompting.

---

## Archive

The `archive/` folder contains earlier Excel and SQL projects.

These are preserved for portfolio history and learning progression, but are not part of the active analytics engine stack.

Active development is focused on `intake_engine/`, `metrics_engine/`, `report_engine/`, and `ai_workflows/`.

---

## Roadmap

### Completed

- **Intake Engine** — clean messy source files and generate analytics-ready outputs
- **Metrics Engine** — create reusable, validated KPI outputs from cleaned data
- **Report Engine** — generate structured report artifacts from trusted metric outputs

### Next Priorities

**End-to-End Demo Workflow** — a polished walkthrough showing messy input → cleaned data → trusted metrics → client-ready report

**Report Quality** — number formatting, metric grouping, and period-over-period display in generated reports

**Visual Layer** — reusable Power BI dashboards or lightweight visualizations that consume trusted Metrics Engine data

**AI-Ready Analytics Layer** — future work may include natural-language analytics interfaces, semantic layers, and workflow automation on top of trusted data

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
