# Power BI Export Contract

## Overview

The Power BI export stage produces a set of CSV files consumed by the reusable Power BI readiness dashboard template. This document defines the schema and semantics for each file. It is the authoritative reference for changes that may break the template.

Files are written to `<output>/powerbi/` when the pipeline is run with `--with-powerbi-export`. The stage is implemented in `visuals_engine/visuals_engine/exporter.py`.

---

## Files

### readiness_kpis.csv

**Purpose:** Overall readiness KPI values for headline card visuals.

**Grain:** One row per metric ID. Latest date, `date_only` rollup level only.

**Required columns:**

| Column | Type | Description |
|---|---|---|
| `metric_id` | string | Metric identifier key |
| `label` | string | Display label for the metric |
| `value` | float | Numeric metric value |
| `unit` | string | Unit string (`%`, `gaps`, `items`, `requirements`) |
| `description` | string | Metric description (empty string if not in dictionary) |

**Required metric_id values — all four must be present:**
- `readiness_completion_pct`
- `total_requirement_count`
- `open_gap_count`
- `critical_item_count`

**Expected Power BI usage:** KPI card visuals on the report header. Measures reference `metric_id` to look up the correct row.

**Breaking changes:** Removing a required column; removing a required `metric_id`; renaming any column; changing value from numeric to string.

**Non-breaking changes:** Adding rows for additional metrics; populating `description` where it was previously empty.

---

### readiness_by_category.csv

**Purpose:** Category-level readiness breakdown for bar chart and table visuals.

**Grain:** One row per category. Latest date, `date_category` rollup level only. No duplicate `category` keys.

**Required columns:**

| Column | Type | Description |
|---|---|---|
| `category` | string | Category display label (friendly name, not internal slug) |
| `readiness_completion_pct` | float | Completion percentage for this category |
| `open_gap_count` | float | Open gap count for this category |

**Grain guarantee:** The `category` column is a unique key. Power BI visuals rely on exactly one row per category.

**Expected Power BI usage:** Horizontal bar chart ranked by completion %; category slicer.

**Breaking changes:** Removing a required column; producing duplicate `category` rows; renaming columns; changing `category` from friendly label to internal slug.

**Non-breaking changes:** File is empty (zero data rows) when no `date_category` data exists — Power BI visuals should handle a no-data state. Additional categories appearing as data grows.

---

### readiness_by_market.csv

**Purpose:** Market-level readiness breakdown for geographic comparison visuals.

**Grain:** One row per market. Latest date, `date_market` rollup level only. No duplicate `market` keys.

**Required columns:**

| Column | Type | Description |
|---|---|---|
| `market` | string | Market identifier |
| `readiness_completion_pct` | float | Completion percentage for this market |
| `open_gap_count` | float | Open gap count for this market |

**Grain guarantee:** The `market` column is a unique key. Power BI visuals rely on exactly one row per market.

**Expected Power BI usage:** Market comparison bar chart; market slicer for cross-filtering.

**Breaking changes:** Removing a required column; producing duplicate `market` rows; renaming columns.

**Non-breaking changes:** File is empty when no `date_market` data exists. New markets appearing as data grows.

---

### validation_summary.csv

**Purpose:** Data quality status for Power BI conditional formatting and data-freshness indicators.

**Grain:** One row representing the most recent metrics validation run.

**Required columns:**

| Column | Type | Description |
|---|---|---|
| `status` | string | Validation status (`passed`, `passed_with_warnings`, `failed`) |
| `error_count` | int | Number of validation errors |
| `warning_count` | int | Number of validation warnings |

**Expected Power BI usage:** Conditional formatting badge on the report header; tooltip showing data quality context.

**Breaking changes:** Removing a required column; renaming columns; changing `status` enum values used in Power BI conditional rules.

**Non-breaking changes:** File is empty when no validation record exists.

---

### metric_dictionary.csv

**Purpose:** Metric metadata for Power BI tooltip text, dynamic labels, and measure descriptions.

**Grain:** One row per metric in the registry. Ordered by `id`.

**Required columns:**

| Column | Type | Description |
|---|---|---|
| `id` | string | Metric identifier (matches `metric_id` in other files) |
| `label` | string | Display label |
| `type` | string | Metric type (e.g., `completion_pct`, `count`, `conditional_count`) |
| `unit` | string | Unit string |
| `decimals` | int | Decimal places for display formatting |
| `description` | string | Full description text |

**Expected Power BI usage:** Lookup table joined to `readiness_kpis.csv` via `id = metric_id` for tooltip and measure descriptions.

**Breaking changes:** Removing a required column; renaming columns; changing `id` values that Power BI measures depend on.

**Non-breaking changes:** Adding new metric rows; updating description text.

---

### client_context.csv (optional)

**Purpose:** Client-specific metadata for personalizing report headers and labels.

**Grain:** Caller-defined. Copied as-is from the source path provided via `--client-context`.

**Presence:** Only written to the output directory when `--client-context <path>` is passed to the pipeline. Absent otherwise. Power BI template must handle both states.

**Common columns (not enforced):** `project_id`, `client_name`, `assessment_date`.

**Expected Power BI usage:** Report title personalization; client logo lookup; slicer labels.

**Breaking changes:** Changes to columns that the Power BI template references must be coordinated with the template owner before deploying.

**Non-breaking changes:** Adding columns the template does not reference.

---

## Change Policy

| Change type | Classification | Required action |
|---|---|---|
| Column added to any CSV | Non-breaking | Update Power BI template to consume or ignore |
| Column removed from any CSV | **Breaking** | Update Power BI template before deploying |
| Column renamed | **Breaking** | Update Power BI template before deploying |
| Required `metric_id` removed from `readiness_kpis.csv` | **Breaking** | Update Power BI measures before deploying |
| New category or market value added | Non-breaking | Power BI visuals adapt automatically |
| File becomes empty (no data) | Non-breaking | Power BI visuals must handle no-data state |
| `status` enum value added to `validation_summary.csv` | Non-breaking if no conditional rule targets it; breaking otherwise | Review conditional formatting rules |

---

## Contract Tests

Contract guarantees in this document are enforced by:

```
analytics_pipeline/tests/analytics_pipeline/test_powerbi_export_contract.py
```

Run with:

```bash
cd analytics_pipeline
python -m pytest tests/analytics_pipeline/test_powerbi_export_contract.py -v
```
