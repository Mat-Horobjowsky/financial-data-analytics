---
name: testing_and_validation
description: Use this before declaring work complete. Run relevant tests and CLI commands, inspect generated outputs, and summarize evidence that the change works.
---

# Testing and Validation Skill

## Purpose

Use this workflow before saying any code change is complete.

The goal is to prove the work runs, outputs are created, and no obvious regressions were introduced.

## When to Use

Use this skill after:

- changing Intake Engine
- changing Metrics Engine
- changing Report Engine
- changing Analytics Store
- changing Visuals Engine
- changing Analytics Pipeline
- changing Power BI export behavior
- editing CLI behavior
- changing package structure
- adding outputs
- fixing bugs
- updating tests
- refactoring code

## Core Principles

- Do not claim success without evidence.
- Prefer targeted tests first, then broader tests if practical.
- Run the actual CLI when the feature is CLI-facing.
- Inspect generated files, not just terminal success.
- Summarize exact commands and results.
- Be honest about untested areas.

## Required Validation Flow

1. Identify affected module.
2. Run targeted tests.
3. Run broader tests if practical.
4. Run the relevant CLI command.
5. Confirm expected output files exist.
6. Inspect at least one output file for columns/shape/content.
7. Check for unrelated file changes.
8. Summarize validation evidence.

## Suggested Commands

Adapt these to the actual repo structure.

```bash
python -m pytest
python -m pytest tests/test_intake_engine.py
python -m pytest tests/test_metrics_engine.py
python -m pytest tests/test_report_engine.py
python -m pytest tests/test_analytics_store.py
python -m pytest tests/test_visuals_engine.py
python -m pytest tests/test_analytics_pipeline.py
python -m pytest tests/test_powerbi_export_contract.py
```

Possible CLI checks:

```bash
python -m intake_engine.cli --help
python -m metrics_engine.cli --help
python -m report_engine.cli --help
python -m visuals_engine.cli --help
python -m analytics_pipeline.cli --help
```

Example build/run checks:

```bash
python -m metrics_engine.cli run --input <input_path> --output <output_path>
python -m report_engine.cli build --input <metrics_output_path> --output <report_output_path>
python -m visuals_engine.cli render --output <output_path>
python -m analytics_pipeline.cli run --input <input_path> --output <output_path>
```

## Artifact Validation

For changes that produce generated artifacts, inspect the files directly:

- **HTML dashboards**: open or inspect the file; confirm expected sections, tables, and values render correctly.
- **Power BI export CSVs**: confirm expected files exist, columns match the contract in `docs/powerbi_export_contract.md`, and grain is correct.
- **Power BI sidecar files**: confirm manifest or metadata files exist and reference the correct export files.
- **PDF outputs**: confirm file is generated and not empty where PDF export is supported.
- **Pipeline summary outputs**: confirm `pipeline_summary.json` or equivalent exists and contains expected stage results.

For changes that affect orchestration or cross-engine artifact handoff, run the end-to-end pipeline flow and verify all stage outputs are produced correctly.

## Validation Summary Format

```md
## Validation Summary

### Commands Run

```bash
command here
```

### Results

- Tests:
- CLI:
- Output files:
- Output inspection:
- Unrelated changes:

### Confidence Level

High / Medium / Low

### Remaining Risks

-
```

## Stop Conditions

Stop and report honestly if:

- tests fail
- CLI command fails
- expected outputs are missing
- import/package paths are broken
- output files exist but are empty or malformed
- validation was not possible

## Anti-Patterns

Avoid:

- saying “should work” as final validation
- only checking code visually
- ignoring failed tests because they seem unrelated
- changing tests to match broken behavior
- deleting failing tests without explicit approval
