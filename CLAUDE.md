# CLAUDE.md

## Mission

Help build this analytics system into a modular, production-minded workflow for turning messy data into trusted metrics and client-ready outputs.

Core direction:

```text
Clean data → trusted metrics → visuals anywhere
```

## Active Product Stack

The active work in this repo is organized around eight areas:

1. **Intake Engine** (`intake_engine/`)
   - Converts messy CSV/XLSX files into clean, analytics-ready datasets.

2. **Metrics Engine** (`metrics_engine/`)
   - Turns clean data into trusted, reusable KPI and metric outputs.

3. **Report Engine** (`report_engine/`)
   - Turns trusted metrics into client-facing reports, summaries, and deliverables.

4. **Analytics Store** (`analytics_store/`)
   - Persists metrics and report outputs into a queryable DuckDB store.

5. **Visuals Engine** (`visuals_engine/`)
   - Renders static HTML dashboards and Power BI-ready CSV exports from the analytics store.

6. **Analytics Pipeline** (`analytics_pipeline/`)
   - Orchestrates Intake → Metrics → Report → Store → Visuals / Power BI Export as a single CLI workflow.

7. **Power BI Export** (stage within `visuals_engine/visuals_engine/exporter.py`)
   - Produces the CSV files consumed by the reusable Power BI readiness dashboard template.
   - Schema contract documented in `docs/powerbi_export_contract.md`.

8. **AI Workflows** (`ai_workflows/`)
   - Workflow skill files that guide AI-assisted development on the engines above.

Future layers such as GUI tools, semantic analytics, or natural-language agents should not be added prematurely.

## Archive

The `archive/` folder contains historical and portfolio projects (SQL analyses, Excel projects, early agent experiments) that are not part of the active engine stack.

Do not modify files in `archive/` unless explicitly requested by the user. Do not reference `archive/` from engine source code.

## AI Workflow Index

Use these workflow files before working on related tasks.

### Repo Inspection

Path:

```text
ai_workflows/repo_inspection/SKILL.md
```

Use before proposing or making code changes. Inspect current files, tests, CLI behavior, and package structure before editing.

### Intake Feature Build

Path:

```text
ai_workflows/intake_feature_build/SKILL.md
```

Use when adding, modifying, or debugging Intake Engine functionality for loading, profiling, cleaning, validating, and exporting messy CSV/XLSX data.

### Metrics Feature Build

Path:

```text
ai_workflows/metrics_feature_build/SKILL.md
```

Use when adding, modifying, or debugging Metrics Engine functionality that turns clean Intake output into trusted KPIs and semantic metric outputs.

### Report Feature Build

Path:

```text
ai_workflows/report_feature_build/SKILL.md
```

Use when adding, modifying, or debugging Report Engine functionality that turns Metrics Engine outputs into client-facing summaries, tables, charts, and report files.

### Visuals Feature Build

Path:

```text
ai_workflows/visuals_feature_build/SKILL.md
```

Use when adding, modifying, or debugging Visuals Engine functionality for static HTML dashboards, Power BI-ready CSV exports, and dashboard artifacts.

### Testing and Validation

Path:

```text
ai_workflows/testing_and_validation/SKILL.md
```

Use before declaring work complete. Run relevant tests and CLI commands, inspect generated outputs, and summarize evidence.

### Documentation Update

Path:

```text
ai_workflows/documentation_update/SKILL.md
```

Use when updating README files, CLI examples, screenshots, project explanations, portfolio documentation, or client-facing notes.

### Scope Discipline

Path:

```text
ai_workflows/scope_discipline/SKILL.md
```

Use whenever a task risks becoming too large, too abstract, or too far from the current engine stack.

## Documentation Discipline

- Update the relevant **engine README** when a user-facing engine behavior changes (new CLI flag, new output file, changed column name, new template, etc.).
- Update the **root README** only for stack-level changes: demo workflow, pipeline usage, install steps, output folder structure, or portfolio-facing descriptions.
- Do **not** update any README for internal-only refactors, test-only changes, temporary debugging, or cosmetic edits that have no user-visible effect.

## Default Working Rules

- Inspect before editing.
- Prefer the smallest useful implementation.
- Use tests where practical.
- Keep modules separate.
- Do not calculate business KPIs in Intake Engine.
- Do not calculate report-specific logic in Metrics Engine.
- Do not redefine metrics in Report Engine.
- Do not add APIs, GUIs, databases, agents, or cloud services unless explicitly requested.
- Do not rewrite working architecture without a clear reason.
- Use relative paths that work from the repo root.
- Make outputs predictable and easy to inspect.
- Be honest about uncertainty and failing tests.
- Do not modify `archive/` unless explicitly requested by the user.
- Treat Power BI export CSVs as a stable downstream contract. Do not rename files, remove columns, change grain, or alter data types without updating `docs/powerbi_export_contract.md` and the contract validation tests.
- When Report Engine logic affects both Markdown and HTML outputs, put shared business/report logic in helpers (e.g. `insights.py`) and keep renderer-specific code in `renderer.py` and `html.py` limited to formatting only.
- Do not calculate business metrics or readiness logic in Visuals Engine. Visuals Engine renders, shapes, and exports already-trusted outputs; analytical logic belongs upstream.
- When changing Analytics Pipeline stage inputs, flags, or artifacts, keep `pipeline_summary.json`, README guidance, and end-to-end tests aligned.

## Standard Response Format Before Editing

When asked to modify the repo, first provide:

```md
## Current Understanding

## Files I Need To Inspect

## Proposed Smallest Safe Change

## Tests / Validation I Will Run

## Approval Needed Before Editing
```

If the user explicitly asks you to edit immediately, proceed carefully but still inspect first.

## Standard Completion Format

After changes, respond with:

```md
## What Changed

## Files Changed

## Commands Run

## Validation Results

## Output Files Created

## Risks / Limitations

## Recommended Next Step
```

## Scope Guardrail

When in doubt, choose the path that strengthens the current stack:

```text
Intake Engine → Metrics Engine → Report Engine → Analytics Store → Visuals / Power BI Export
```

Avoid building a broad analytics platform before the file-based workflow is stable, tested, documented, and demo-ready.
