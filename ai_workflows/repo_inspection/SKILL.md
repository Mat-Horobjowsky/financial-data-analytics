---
name: repo_inspection
description: Use this before proposing or making code changes. Inspect the current repository state, understand the module boundaries, identify relevant files/tests/CLIs, and summarize the safest next step before editing.
---

# Repo Inspection Skill

## Purpose

Use this workflow whenever you need to understand the current repo before making recommendations or code changes.

The goal is to avoid guessing, avoid duplicate work, and avoid changing the wrong module.

## When to Use

Use this skill when the user asks to:

- inspect the current project state
- continue work from a previous session
- debug a command or import error
- decide what to build next
- propose an implementation plan
- modify Intake Engine, Metrics Engine, Report Engine, or shared tooling

## Core Principles

- Inspect before editing.
- Prefer the smallest safe change.
- Do not assume file paths, package names, or CLI commands.
- Do not rewrite working architecture unless there is a clear reason.
- Separate observation from recommendation.
- Ask for approval before editing if the user requested a plan first.

## Required Steps

1. Identify the current working directory.
2. List the relevant repo structure.
3. Locate the module related to the task:
   - `intake_engine/`
   - `metrics_engine/`
   - `report_engine/`
   - shared utilities
   - tests
   - docs
4. Inspect relevant files before proposing changes.
5. Inspect relevant tests.
6. Inspect CLI entry points and package configuration.
7. Run existing tests or targeted commands only when appropriate.
8. Summarize findings before editing.

## Output Format

When inspection is complete, respond with:

```md
## Current Repo State

- Relevant module:
- Relevant files:
- Existing tests:
- Existing CLI/package setup:
- What appears to be working:
- What appears broken or missing:

## Recommendation

Smallest safe next step:

## Proposed Implementation Plan

1.
2.
3.

## Do Not Edit Yet / Ready to Edit

State whether edits should wait for user approval.
```

## Stop Conditions

Stop and ask for direction if:

- the requested change affects multiple modules unexpectedly
- imports/package structure are unclear
- tests are failing for unrelated reasons
- the safest implementation requires changing public interfaces
- the user explicitly requested no edits until approval

## Anti-Patterns

Avoid:

- creating new architecture before inspecting existing architecture
- adding dependencies without justification
- changing multiple engines for a single feature unless required
- deleting files without explicit approval
- claiming something works without running or inspecting evidence
