---
name: visuals_feature_build
description: Use this when adding, modifying, or debugging Visuals Engine functionality for rendering static HTML dashboards, producing Power BI-ready CSV exports, and shaping dashboard artifacts from the analytics store.
---

# Visuals Feature Build Skill

## Purpose

Use this workflow to safely extend `visuals_engine`.

The Visuals Engine renders trusted upstream outputs into static HTML dashboards and Power BI-ready CSV exports. It consumes data from the Analytics Store and does not redefine metrics, readiness logic, or report insights.

## When to Use

Use this skill when the user asks to:

- add or modify static HTML dashboard rendering
- add or modify Power BI export CSV outputs
- change dashboard layout, sections, or formatting
- change export file structure or column shaping
- debug Visuals Engine CLI behavior
- inspect or verify generated dashboard or export artifacts
- add sidecar files (metadata, summaries) for export packages

## Core Principles

- Visuals consume trusted upstream outputs; they do not produce metrics.
- Do not recalculate metrics, readiness logic, or report insights in Visuals Engine.
- Treat Power BI export CSVs as a stable downstream contract.
- Inspect generated HTML and CSV artifacts directly, not only test results.
- Preserve module boundaries: rendering and export shaping belong here; analytical logic belongs upstream.
- Keep outputs predictable, organized, and easy to inspect.

## Expected Responsibilities

The Visuals Engine may handle:

- reading from the Analytics Store (DuckDB) or trusted upstream CSVs
- rendering static HTML dashboards
- producing Power BI-ready CSV exports
- organizing dashboard artifact folders
- producing sidecar files (export manifests, metadata)
- applying display formatting, layout, and styling to dashboards
- applying column shaping and grain for export files

## Required Build Flow

1. Inspect current Visuals Engine files and tests.
2. Inspect the Analytics Store schema and relevant query patterns.
3. Confirm what upstream outputs are consumed (DuckDB tables, CSVs).
4. Identify the smallest change boundary.
5. For Power BI export changes: inspect `docs/powerbi_export_contract.md` first.
6. Add or update tests where practical.
7. Implement the smallest working change.
8. Run targeted tests.
9. Run the Visuals Engine CLI.
10. Inspect generated HTML and CSV artifact files directly.
11. If the Power BI export schema changed, update `docs/powerbi_export_contract.md` and contract validation tests.
12. Update docs if behavior changed.
13. Use `ai_workflows/testing_and_validation/SKILL.md` before declaring work complete.

## Design Rules

### HTML Dashboards

- Do not embed metric calculation logic in dashboard templates.
- Do not hardcode absolute paths.
- Keep layout and styling separate from data selection logic.
- Make dashboard outputs self-contained and openable without a server.

### Power BI Export

- The Power BI export CSV schema is a stable downstream contract.
- Do not rename files, remove columns, change grain, or alter data types without:
  - updating `docs/powerbi_export_contract.md`
  - updating contract validation tests
  - updating relevant docs and examples
- Prefer additive changes (new optional columns) over breaking changes.
- Keep export file names consistent with the contract.

### General

- Do not recalculate readiness thresholds or KPI formulas in Visuals Engine.
- Do not duplicate Analytics Store or Metrics Engine logic.
- Artifact folder structure should be predictable and documented.

## Output Format for Work Summary

```md
## Visuals Change Summary

- Feature:
- Artifacts changed (HTML / CSV / sidecar):
- Power BI contract affected (yes/no):
- Files changed:
- Tests added/updated:
- CLI command tested:
- Outputs generated and inspected:
- Risks or limitations:
- Recommended next step:
```

## Stop Conditions

Stop and ask before proceeding if:

- the change would alter Power BI export file names, columns, grain, or types without explicit user approval
- the requested logic belongs in Metrics Engine, Report Engine, or Analytics Store instead
- the Analytics Store schema does not contain the expected data
- dashboard rendering requires redefining a metric or readiness threshold
- the user asked for a plan before edits

## Anti-Patterns

Avoid:

- calculating business metrics or readiness logic in Visuals Engine
- duplicating metric definitions from Metrics Engine
- changing Power BI export schema without updating the contract and tests
- building a second dashboard layer or orchestration path when Visuals Engine already provides the correct extension point
- making dashboard outputs dependent on manual file movement
- adding APIs, GUIs, or agents unless explicitly requested
