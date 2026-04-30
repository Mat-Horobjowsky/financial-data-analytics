---
name: metrics_feature_build
description: Use this when adding, modifying, or debugging Metrics Engine functionality that turns clean Intake Engine output into trusted KPIs, semantic metrics, and reusable analytical outputs.
---

# Metrics Feature Build Skill

## Purpose

Use this workflow to safely extend `metrics_engine`.

The Metrics Engine turns clean data into trusted, reusable metrics.

## When to Use

Use this skill when the user asks to:

- add a new KPI
- validate metric calculations
- create wide or narrow metric outputs
- add time-based metrics
- add year-to-date, rolling, or comparison metrics
- improve semantic metric definitions
- prepare outputs for reports, dashboards, or AI analysis
- debug Metrics Engine CLI behavior

## Core Principles

- Metrics must be explainable.
- Keep KPI definitions centralized.
- Avoid hardcoded client-specific logic.
- Separate metric calculation from presentation.
- Preserve compatibility with Report Engine.
- Make outputs easy for Power BI, DuckDB, Python, and future agents to consume.
- Trusted metrics matter more than clever metrics.

## Expected Responsibilities

The Metrics Engine may handle:

- loading cleaned Intake output
- validating required columns
- calculating KPIs
- generating metric tables
- producing wide and/or long/narrow outputs
- producing metric metadata
- creating validation summaries
- preparing data for reporting and visualization

## Required Build Flow

1. Inspect current Metrics Engine files and tests.
2. Identify existing metric patterns.
3. Confirm expected input from Intake Engine.
4. Define the metric formula clearly.
5. Add or update tests with small sample data.
6. Implement the smallest working change.
7. Run targeted tests.
8. Run the Metrics Engine CLI.
9. Inspect output files.
10. Update docs if the public interface changed.
11. Use `ai_workflows/testing_and_validation/SKILL.md` before declaring work complete.

## Metric Definition Standard

Every new metric should be documented with:

```md
Metric name:
Business meaning:
Formula:
Input columns:
Output column:
Grain:
Null handling:
Edge cases:
Example:
```

## Output Rules

Metrics outputs should be predictable and machine-readable.

Preferred outputs may include:

```text
wide_metrics.csv
long_metrics.csv
metric_definitions.csv
validation_summary.json
```

## Design Rules

- Do not bury metric formulas inside report templates.
- Do not calculate metrics only in Power BI if they belong in the semantic layer.
- Do not mix display formatting with metric calculation.
- Do not assume date columns exist unless validated.
- Do not invent missing values unless rules are explicit.
- Prefer clear column names over clever abstractions.

## Output Format for Work Summary

```md
## Metrics Change Summary

- Feature / metric:
- Formula:
- Input columns:
- Files changed:
- Tests added/updated:
- CLI command tested:
- Outputs generated:
- Risks or limitations:
- Recommended next step:
```

## Stop Conditions

Stop and ask before proceeding if:

- the metric definition is ambiguous
- required input columns do not exist
- calculation grain is unclear
- null handling could materially affect results
- the requested change belongs in Intake Engine or Report Engine

## Anti-Patterns

Avoid:

- report-specific formatting in Metrics Engine
- client-specific one-off KPIs in core logic
- changing existing metric definitions without documenting the change
- adding complex semantic-layer infrastructure too early
- adding APIs, GUIs, or agents unless explicitly requested
