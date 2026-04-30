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
- document Intake → Metrics → Report workflow

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
- Future visual/dashboard/agent layers can consume the same trusted outputs.

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
