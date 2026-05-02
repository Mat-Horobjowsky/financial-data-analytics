# analytics_pipeline v0.1

Stage-based orchestrator for the Intake → Metrics → Report pipeline.

Runs all three engines in sequence from a single command. Stops at the first failed stage and writes a `pipeline_summary.json` recording the status, command, and generated files for every stage.

## Usage

```bash
cd analytics_pipeline
analytics-pipeline run \
  --input ../intake_engine/tests/fixtures/messy_data_center_sample_for_intake.csv \
  --output outputs/demo \
  --with-time \
  --template full_report
```

## CLI flags

| Flag | Default | Description |
|---|---|---|
| `--input` | *(required)* | Raw input file (CSV or XLSX) |
| `--output` | `outputs/pipeline` | Pipeline output root directory |
| `--with-time` | off | Enable prior-period time analysis in Metrics Engine |
| `--template` | `full_report` | Report template (`full_report`, `executive_summary`, `metrics_detail`) |

## Output structure

```
<pipeline_output>/
├── intake/          # Intake Engine outputs (clean CSV, validation JSON, ...)
├── metrics/         # Metrics Engine outputs (long/wide metrics, metric dictionary, ...)
├── report/          # Report Engine outputs (report.html, report.md, insights.json, ...)
└── pipeline_summary.json
```

### pipeline_summary.json

```json
{
  "pipeline_version": "0.1.0",
  "generated_at": "...",
  "input_path": "...",
  "output_dir": "...",
  "with_time": true,
  "template": "full_report",
  "status": "success",
  "stages": {
    "intake":  {"status": "success", "command": "...", "output_dir": "...", "generated_files": [...]},
    "metrics": {"status": "success", "command": "...", "output_dir": "...", "generated_files": [...]},
    "report":  {"status": "success", "command": "...", "output_dir": "...", "generated_files": [...], "template": "full_report"}
  },
  "future_stages": ["store", "visuals"]
}
```

## Prerequisites

All three engines must be installed before running the pipeline:

```bash
cd intake_engine && pip install -e . && cd ..
cd metrics_engine && pip install -e . && cd ..
cd report_engine && pip install -e . && cd ..
cd analytics_pipeline && pip install -e . && cd ..
```

## Setup

```bash
cd analytics_pipeline
pip install -e ".[dev]"
pytest
```

## Architecture

| Module | Role |
|---|---|
| `stages.py` | Stage definitions — `StageContext`, `StageResult`, command builders, `ACTIVE_STAGES` |
| `runner.py` | Executes stages sequentially, stops on first failure |
| `summary.py` | Builds and writes `pipeline_summary.json` |
| `cli.py` | `analytics-pipeline run` entry point |

To add a future stage (e.g. `store`), add a command builder function and append `("store", build_store_cmd)` to `ACTIVE_STAGES` in `stages.py`. No other files need to change.
