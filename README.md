# Financial Data Analytics

A growing portfolio of analytics systems, projects, and tools focused on turning raw data into decision-ready intelligence.

This repository documents my progression from analyst workflows to reusable analytics systems — combining data ingestion, metric governance, BI reporting, and AI-ready data foundations.

## 📂 Repository Structure

```text
financial-data-analytics/
├── intake_engine/       # Raw/messy data → clean analytics-ready data
├── metrics_engine/      # Clean data → trusted reusable KPI outputs
├── sql/                 # SQL analytics and modeling projects
├── powerbi/             # Power BI dashboards and report assets
├── excel/               # Excel-based models and analysis
└── README.md

🚀 Featured Projects
Intake Engine v1.0 ✅

A modular Python CLI ingestion tool that converts messy CSV / TSV / Excel files into trusted analytics-ready outputs.

Key Features
CSV / TSV / Excel ingestion
Delimiter auto-detection
Multi-sheet Excel support
Data cleaning and normalization
Validation and profiling
HTML quality reports
DuckDB loading and append mode
YAML configs
Batch processing
Metrics Engine v1.0 ✅

A config-driven KPI calculation engine that turns cleaned data into validated, reusable metric outputs for Power BI, Excel, and future AI analytics workflows.

Key Features
CSV / Excel input
Schema-driven column normalization
YAML-based metric definitions
Validation before calculation
Configurable segment rollups
Sum-before-divide KPI logic
Long and wide metric outputs
Metric dictionary generation
Validation report export
CLI workflow with tests
Example Workflow
Cleaned Intake Engine output
        ↓
Metrics Engine validation
        ↓
Trusted KPI calculation
        ↓
Power BI / Excel-ready outputs

Generated outputs:

long_metrics.csv
wide_metrics.csv
metric_dictionary.csv
validation_report.json
🧠 Roadmap
Intake Engine ✅

Clean data.

Metrics Engine ✅

Trusted KPI logic and reusable business metrics.

Visual Layer 🔜

Power BI dashboards, reusable report templates, and eventually natural-language analytics interfaces.

AI-Ready Analytics Layer 🔜

Future work focused on connecting clean data and trusted metrics to agentic workflows, semantic layers, and natural-language analysis.

🧰 Skills Demonstrated
Python analytics engineering
Data ingestion and cleaning automation
Schema normalization
KPI / metric layer design
SQL data modeling
Power BI reporting
DuckDB workflows
YAML-driven configuration
Data quality validation
Modular system architecture
Test-driven development
Git / GitHub workflow
🎯 Purpose

The goal of this repo is to build a practical analytics product stack around a simple principle:

Clean data → Trusted metrics → Visuals anywhere

This work reflects my transition from dashboard-building toward AI-enabled analytics systems: reusable tools that clean data, standardize metric logic, and make reporting more trustworthy and scalable.

📫 Connect

LinkedIn: www.linkedin.com/in/mat-horobjowsky