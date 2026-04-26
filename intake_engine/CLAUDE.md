# CLAUDE.md

## Mission

Help build **intake_engine** into a production-grade data intake tool that converts messy CSV/XLSX files into clean, analytics-ready datasets.

Prioritize real execution over theory.

---

## Core Build Principles

1. **Ship small, iterate fast**
   Build the smallest useful version first. Avoid premature complexity.

2. **Scalable architecture**
   Design so features can be added without rewrites.

3. **Modular structure**
   Use clear separation of concerns (loader, cleaner, profiler, exporter, cli, models, utils).

4. **Reusable components**
   Write generic functions/modules that can serve multiple pipelines and future products.

5. **Production quality**
   Readable code, typed where useful, strong error handling, logs, tests.

6. **Pragmatic over perfect**
   Choose practical solutions that work now. Optimize later when justified.

---

## Engineering Preferences

* Python-first
* Prefer simple dependencies
* Use `polars` for dataframes
* Use `typer` for CLI
* Use `pydantic` for models/configs
* Use `pytest` for tests
* Pure functions where possible
* Config-driven when valuable

---

## Code Standards

* Keep files focused and concise
* Avoid unnecessary abstractions
* Avoid deep nesting
* Prefer explicit over clever
* Maintain backward compatibility when possible
* Refactor only when ROI is clear

---

## Decision Framework

When proposing changes, prioritize:

1. User value
2. Simplicity
3. Maintainability
4. Reusability
5. Performance

---

## Output Expectations

When asked to build:

1. Implement directly
2. Keep code concise
3. Include tests
4. Explain only what matters
5. Suggest next highest-ROI step

---

## Anti-Patterns

* Overengineering
* Fancy architecture with no usage
* Premature microservices
* Unnecessary dependencies
* Rewriting working code
* Building features without evidence

---

## Current Focus

Turn intake_engine into a trustworthy ingestion layer for analytics and consulting workflows.
