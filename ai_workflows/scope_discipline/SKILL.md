---
name: scope_discipline
description: Use this whenever a task risks becoming too large, introducing premature architecture, or distracting from the current Intake → Metrics → Report roadmap. Enforce small, modular, high-ROI implementation.
---

# Scope Discipline Skill

## Purpose

Use this workflow to prevent overbuilding.

The project should grow through small, reusable, working modules rather than large unfinished architecture.

## When to Use

Use this skill when the user or agent considers adding:

- APIs
- databases
- GUIs
- dashboards
- agent orchestration
- MCP
- RAG
- cloud services
- plugin systems
- complex configuration systems
- broad refactors
- multi-module redesigns

## Core Principle

Build the smallest useful version that strengthens the current architecture.

The strategic direction is:

```text
Clean data → trusted metrics → visuals anywhere
```

But the implementation should move one practical step at a time.

## Decision Checklist

Before adding complexity, answer:

```md
1. Does this solve a current blocker?
2. Does this improve the current module directly?
3. Can this be done with existing architecture?
4. Can this be built in one small testable step?
5. Will this make future modules easier, not harder?
6. Is there a simpler file-based version first?
7. Does the user explicitly need this now?
```

If the answer is mostly no, do not build it yet.

## Preferred Build Order

Prefer this order:

1. Working file-based CLI
2. Tests
3. Clean outputs
4. Documentation
5. Small integration wrapper
6. Static report/demo
7. Optional GUI
8. Optional database layer
9. Optional natural-language/agent layer
10. Optional APIs/cloud deployment

## Allowed Complexity

Complexity is acceptable when:

- current code is blocked without it
- it reduces repeated manual work
- it preserves module boundaries
- it is testable
- it has a clear user-facing benefit
- it does not force a rewrite

## Output Format

When evaluating scope, respond with:

```md
## Scope Check

Recommendation: Build / Delay / Reject / Simplify

## Why

## Smallest Useful Version

## What Not To Build Yet

## Future Upgrade Path
```

## Anti-Patterns

Avoid:

- building a platform before the core workflow works
- adding APIs before file-based outputs are stable
- adding a GUI before CLI workflow is reliable
- adding RAG before documents and schemas are organized
- adding agents before workflow rules are documented
- redesigning working modules for theoretical future needs
- introducing dependencies that make the repo harder to run
