---
name: intake_feature_build
description: Use this when adding, modifying, or debugging Intake Engine functionality for loading, profiling, cleaning, validating, and exporting messy CSV/XLSX data into analytics-ready datasets.
---

# Intake Feature Build Skill

## Purpose

Use this workflow to safely extend `intake_engine`.

The Intake Engine converts messy CSV/XLSX files into clean, validated, analytics-ready datasets.

## When to Use

Use this skill when the user asks to:

- add a new intake feature
- improve data cleaning
- handle messy CSV or Excel files
- improve profiling
- improve validation summaries
- export cleaned files
- debug Intake Engine CLI behavior
- prepare Intake output for Metrics Engine

## Core Principles

- Preserve raw input data.
- Never silently drop columns.
- Make cleaning decisions explainable.
- Prefer deterministic transformations over hidden magic.
- Keep client-specific logic out of core engine code.
- Keep the CLI simple and reliable.
- Build small, testable improvements.
- Maintain compatibility with downstream Metrics Engine inputs.

## Expected Responsibilities

The Intake Engine may handle:

- file loading
- column normalization
- type inference
- missing value profiling
- duplicate detection
- basic cleaning
- validation summaries
- cleaned CSV/XLSX output
- metadata or profile output
- optional DuckDB-ready exports

## Required Build Flow

1. Inspect current Intake Engine files and tests.
2. Identify the smallest feature boundary.
3. Write or update tests first when practical.
4. Implement the smallest working change.
5. Run targeted tests.
6. Run the relevant CLI command.
7. Inspect generated output files.
8. Update documentation or examples if behavior changed.
9. Use `ai_workflows/testing_and_validation/SKILL.md` before declaring work complete.

## Design Rules

### Loading

- Support CSV first.
- Support XLSX only where existing dependencies allow.
- Avoid adding heavy dependencies unless necessary.
- Return clear errors for unsupported formats.

### Cleaning

- Do not overwrite raw files.
- Do not drop columns unless explicitly requested.
- Keep original-to-cleaned column mapping when possible.
- Normalize column names consistently.
- Avoid guessing business meaning from column names.

### Validation

Validation output should make issues visible:

- row count
- column count
- missing values
- duplicate rows
- inferred data types
- suspicious columns
- warnings
- output file paths

### Outputs

Prefer predictable output names such as:

```text
cleaned_data.csv
profile_summary.csv
validation_summary.json
column_mapping.csv
```

## Output Format for Work Summary

```md
## Intake Change Summary

- Feature:
- Files changed:
- Tests added/updated:
- CLI command tested:
- Outputs generated:
- Risks or limitations:
- Recommended next step:
```

## Stop Conditions

Stop and ask before proceeding if:

- the feature would require redesigning the engine
- the task requires destructive cleaning
- there is ambiguity about how to treat data loss
- the requested change belongs in Metrics Engine instead
- the requested change belongs in Report Engine instead

## Anti-Patterns

Avoid:

- adding dashboard/report logic to Intake Engine
- calculating business KPIs in Intake Engine
- creating client-specific cleaning rules in core logic
- relying on manual file paths that break portability
- adding APIs, GUIs, or databases unless explicitly requested
