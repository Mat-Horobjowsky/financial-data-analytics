import json
from pathlib import Path

import pandas as pd

from metrics_engine.validator import ValidationReport


def export(
    long_metrics: pd.DataFrame,
    wide_metrics: pd.DataFrame,
    metric_dictionary: pd.DataFrame,
    validation_report: ValidationReport,
    output_dir: str | Path,
) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    long_metrics.to_csv(out / "long_metrics.csv", index=False)
    wide_metrics.to_csv(out / "wide_metrics.csv", index=False)
    metric_dictionary.to_csv(out / "metric_dictionary.csv", index=False)

    (out / "validation_report.json").write_text(
        json.dumps(
            {
                "status": validation_report.status,
                "errors": validation_report.errors,
                "warnings": validation_report.warnings,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
