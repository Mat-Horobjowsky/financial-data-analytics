---
name: documentation_update
description: Use this when updating README files, usage examples, screenshots, CLI instructions, output documentation, portfolio notes, or client-facing explanation for the analytics engines.
---

# Documentation Update Skill

## Purpose

Use this workflow to keep project documentation accurate, useful, and portfolio-ready.

Documentation should help a future user, client, recruiter, or AI coding assistant understand what the project does and how to run it.

## When to Use

Use this skill when the user asks to:

- update README
- document CLI usage
- document outputs
- add examples
- explain architecture
- prepare a LinkedIn/project showcase
- add screenshots
- document tests
- document the Intake → Metrics → Report → Analytics Store → Visuals / Power BI Export workflow
- document Analytics Pipeline usage, flags, or artifact folders
- document Visuals Engine outputs or dashboard artifacts
- document or update the Power BI export contract or schema
- document HTML or PDF report outputs

## Core Principles

- Keep docs accurate to the current code.
- Prefer clear examples over abstract explanation.
- Do not exaggerate capabilities.
- Make setup and run commands copy-pasteable.
- Highlight business value and technical value.
- Keep the project portfolio-friendly.
- Document limitations honestly.

## Required Documentation Flow

1. Inspect current code or outputs before documenting behavior.
2. Confirm correct CLI commands.
3. Confirm expected input/output paths.
4. Document what the module does.
5. Document what it does not do yet.
6. Include example commands.
7. Include expected output files.
8. Include troubleshooting notes if relevant.
9. Keep wording concise and professional.

## Recommended README Structure

```md
# Project / Module Name

## Purpose

## What It Does

## Why It Matters

## Project Structure

## Quick Start

## Example Command

## Inputs

## Outputs

## Validation / Tests

## Current Limitations

## Roadmap
```

## Documentation Standards

### Good

```md
Run the Metrics Engine:

```bash
python -m metrics_engine.cli run --input data/sample_clean.csv --output outputs/intake_test
```

This creates:

- `wide_metrics.csv`
- `long_metrics.csv`
- `validation_summary.json`
```

### Bad

```md
This tool uses AI to revolutionize analytics.
```

Avoid vague claims.

## Portfolio Positioning

When relevant, frame the system around:

```text
Clean data → trusted metrics → visuals anywhere
```

Useful positioning:

- Intake Engine cleans messy files.
- Metrics Engine creates trusted KPI outputs.
- Report Engine turns metrics into client-ready deliverables.
- Analytics Store persists metrics and report outputs into a queryable DuckDB store.
- Visuals Engine renders static HTML dashboards and Power BI-ready CSV exports.
- Analytics Pipeline orchestrates the full workflow end-to-end via a single CLI.

## Public Contract Reminder

Before completing a documentation update, confirm whether any public output contracts changed:

- Power BI export schema, file names, grain, or data types → update `docs/powerbi_export_contract.md`.
- Analytics Pipeline artifact folders or stage outputs → update pipeline README and usage examples.
- Report or dashboard deliverables → update engine README and any relevant output examples.

## Stop Conditions

Stop and inspect more if:

- commands are uncertain
- file names are uncertain
- output behavior changed
- docs conflict with tests or code
- screenshots do not match current outputs

## Anti-Patterns

Avoid:

- documenting planned features as completed features
- using inflated marketing language
- adding long theory sections that do not help users run the project
- hiding limitations
- putting stale commands in README
