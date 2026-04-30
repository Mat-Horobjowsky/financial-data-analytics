---
name: report_feature_build
description: Use this when adding, modifying, or debugging Report Engine functionality that turns trusted Metrics Engine outputs into client-facing summaries, report files, tables, charts, and narrative outputs.
---

# Report Feature Build Skill

## Purpose

Use this workflow to safely extend `report_engine`.

The Report Engine turns trusted metrics into clear, client-facing outputs.

## When to Use

Use this skill when the user asks to:

- generate reports from Metrics Engine outputs
- add report templates
- create summaries
- create static report files
- add tables, charts, or narrative sections
- debug Report Engine CLI behavior
- prepare outputs for portfolio demos or client handoff

## Core Principles

- Reports consume metrics; they should not redefine metrics.
- Separate data logic from presentation logic.
- Keep templates reusable.
- Make outputs professional and client-readable.
- Prefer static, reliable reports before complex interactive features.
- Preserve clear handoff from Intake → Metrics → Report.

## Expected Responsibilities

The Report Engine may handle:

- reading Metrics Engine outputs
- selecting report sections
- formatting summary tables
- generating narrative insights
- exporting markdown, HTML, PDF-ready, or other static outputs
- organizing report artifacts
- creating a reproducible report folder

## Required Build Flow

1. Inspect current Report Engine files and tests.
2. Confirm expected Metrics Engine input path.
3. Identify report output format.
4. Keep metric calculations out of Report Engine.
5. Add or update tests where practical.
6. Implement the smallest useful report feature.
7. Run the Report Engine CLI.
8. Inspect generated report outputs.
9. Confirm file paths and relative imports work from repo root.
10. Update docs or examples if behavior changed.
11. Use `ai_workflows/testing_and_validation/SKILL.md` before declaring work complete.

## Report Design Standard

Each report feature should define:

```md
Report section:
Purpose:
Input file(s):
Required columns:
Output format:
Display rules:
Failure behavior:
Example output:
```

## Output Rules

Report outputs should be organized and predictable.

Preferred output structure:

```text
outputs/
└── report_name/
    ├── report.md
    ├── report.html
    ├── tables/
    ├── charts/
    └── summary.json
```

## Design Rules

- Do not calculate core KPIs in Report Engine.
- Do not hardcode absolute local paths.
- Do not require manual file movement.
- Do not make the report dependent on Power BI.
- Keep text generation grounded in available metric outputs.
- Flag missing data instead of hallucinating insights.

## Output Format for Work Summary

```md
## Report Change Summary

- Feature:
- Input files:
- Output files:
- Files changed:
- Tests added/updated:
- CLI command tested:
- Report artifacts generated:
- Risks or limitations:
- Recommended next step:
```

## Stop Conditions

Stop and ask before proceeding if:

- required Metrics Engine outputs are missing
- report content would require unsupported assumptions
- requested visuals require a separate visualization module
- the task requires changing metric definitions
- user asked for a plan before edits

## Anti-Patterns

Avoid:

- duplicating Metrics Engine calculations
- mixing report templates with data cleaning
- adding dashboard infrastructure before static reports work
- over-designing templates before one useful report works
- using vague AI-generated commentary not supported by data
