# Financial Data Analytics

A modular analytics engineering portfolio focused on turning raw data into decision-ready intelligence.

This repository documents my progression from analyst workflows to reusable analytics systems — combining data ingestion, metric governance, reporting automation, BI workflows, and AI-ready data foundations.

The core principle behind this repo is:

Clean data → Trusted metrics → Visuals anywhere

Repository Structure

financial-data-analytics/
├── intake_engine/        # Raw/messy data → clean analytics-ready data
├── metrics_engine/       # Clean data → trusted reusable KPI outputs
├── report_engine/        # Trusted metrics → client-ready reports
├── ai_workflows/         # Reusable AI workflow instructions for coding assistants
├── archive/              # Historical Excel, SQL, and learning projects
├── CLAUDE.md             # Repo-level AI coding assistant guidance
└── README.md

Active Product Stack

This repo is now organized around a three-engine analytics workflow:

Intake Engine
    ↓
Metrics Engine
    ↓
Report Engine

Each engine is designed as a reusable Python CLI package with tests, documented outputs, and a clear role in the analytics pipeline.

Featured Projects

Intake Engine

A modular Python CLI ingestion tool that converts messy CSV, TSV, and Excel files into clean, analytics-ready outputs.

Purpose

The Intake Engine solves the first problem in most analytics workflows: messy source files.

It helps standardize raw data before it reaches dashboards, metric layers, reports, or downstream analysis.

Key Features
CSV, TSV, and Excel ingestion
Delimiter auto-detection
Multi-sheet Excel support
Data cleaning and normalization
Validation and profiling
HTML quality reports
DuckDB loading and append mode
YAML-based configuration
Batch processing
CLI workflow
Test coverage

Standard Setup

cd intake_engine
pip install -e ".[dev]"

CLI

intake --help

Metrics Engine

A config-driven KPI calculation engine that turns cleaned data into validated, reusable metric outputs for Power BI, Excel, reporting tools, and future AI analytics workflows.

Purpose

The Metrics Engine creates a trusted semantic layer for business metrics.

Instead of calculating KPIs separately in dashboards, spreadsheets, and reports, metric logic is centralized, tested, and reusable.

Key Features
CSV and Excel input
Schema-driven column normalization
YAML-based metric definitions
Validation before calculation
Configurable segment rollups
Sum-before-divide KPI logic
Long and wide metric outputs
Metric dictionary generation
Validation report export
CLI workflow
Test coverage

Standard Setup

cd metrics_engine
pip install -e ".[dev]"

CLI

metrics-engine --help

Example Outputs

long_metrics.csv
wide_metrics.csv
metric_dictionary.csv
validation_report.json

Report Engine

A lightweight reporting engine that converts trusted Metrics Engine outputs into client-ready report artifacts.

Purpose

The Report Engine is the reporting layer of the stack.

It takes validated metric outputs and turns them into structured deliverables that can support client handoff, portfolio demos, executive summaries, and future reporting automation.

Key Features
Reads Metrics Engine outputs
Generates report-ready summaries
Produces structured report artifacts
Keeps reporting logic separate from metric logic
CLI workflow
Test coverage
Designed for future report templates, dashboards, and natural-language analytics layers

Standard Setup

cd report_engine
pip install -e ".[dev]"

CLI

report-engine --help

Example End-to-End Workflow

Raw CSV / Excel files
        ↓
Intake Engine
        ↓
Cleaned analytics-ready data
        ↓
Metrics Engine
        ↓
Trusted KPI outputs
        ↓
Report Engine
        ↓
Client-ready report artifacts
        ↓
Power BI / Excel / dashboards / AI analytics workflows

AI Workflows

The ai_workflows/ folder contains reusable workflow instructions for AI coding assistants.

These workflows help keep future development consistent, modular, and scoped.

Current workflow skills include:

repo_inspection
intake_feature_build
metrics_feature_build
report_feature_build
testing_and_validation
documentation_update
scope_discipline

These are used alongside CLAUDE.md to guide future development and reduce repeated prompting.

The goal is to make the repo easier to inspect, extend, test, and document with AI coding tools while preserving clear architecture.

Archive

The archive/ folder contains earlier Excel and SQL projects.

These projects are preserved for portfolio history and learning progression, but they are not part of the active analytics engine stack.

Active development is focused on:

intake_engine/
metrics_engine/
report_engine/
ai_workflows/

Roadmap

Completed

Intake Engine

Clean messy source files and generate analytics-ready outputs.

Metrics Engine

Create reusable, validated KPI outputs from cleaned data.

Report Engine

Generate structured report artifacts from trusted metric outputs.

Next Priorities

End-to-End Demo Workflow

Create a polished demo showing:

messy input file → cleaned data → trusted metrics → client-ready report

Documentation Polish

Improve each engine README with:

setup instructions
CLI examples
input/output examples
screenshots
demo walkthroughs
Visual Layer

Add reusable Power BI dashboards, report templates, or lightweight visualization outputs that consume trusted Metrics Engine data.

AI-Ready Analytics Layer

Future work may include natural-language analytics interfaces, semantic layers, agent-ready documentation, and workflow automation on top of clean data and trusted metrics.

Skills Demonstrated
Python analytics engineering
Data ingestion and cleaning automation
Schema normalization
KPI and metric layer design
Report automation
SQL data modeling
Power BI reporting
DuckDB workflows
YAML-driven configuration
Data quality validation
Modular system architecture
Test-driven development
CLI tool design
Git and GitHub workflow
AI-assisted software development workflows
Purpose

This repo reflects my transition from dashboard-building toward AI-enabled analytics systems.

The goal is to build reusable tools that:

clean messy source data,
standardize metric logic,
produce trusted reporting outputs,
and prepare analytics workflows for dashboards, automation, and AI agents.

In short:

Clean data → Trusted metrics → Visuals anywhere

Connect

LinkedIn: www.linkedin.com/in/mat-horobjowsky