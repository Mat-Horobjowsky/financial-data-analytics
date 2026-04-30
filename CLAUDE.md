# CLAUDE.md

## Mission

Help build this analytics system into a modular, production-minded workflow for turning messy data into trusted metrics and client-ready outputs.

Core direction:

```text
Clean data → trusted metrics → visuals anywhere
```

## Active Product Stack

The active work in this repo is organized around four areas:

1. **Intake Engine** (`intake_engine/`)
   - Converts messy CSV/XLSX files into clean, analytics-ready datasets.

2. **Metrics Engine** (`metrics_engine/`)
   - Turns clean data into trusted, reusable KPI and metric outputs.

3. **Report Engine** (`report_engine/`)
   - Turns trusted metrics into client-facing reports, summaries, and deliverables.

4. **AI Workflows** (`ai_workflows/`)
   - Workflow skill files that guide AI-assisted development on the engines above.

Database support (e.g. DuckDB) may exist in early form within some engines, but should remain secondary to the file-based Intake → Metrics → Report workflow until that workflow is stable, tested, and demo-ready. Future layers such as dashboards, GUI tools, semantic analytics, or natural-language agents should not be added prematurely.

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

Use whenever a task risks becoming too large, too abstract, or too far from the current Intake → Metrics → Report roadmap.

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
Intake Engine → Metrics Engine → Report Engine
```

Avoid building a broad analytics platform before the file-based workflow is stable, tested, documented, and demo-ready.
