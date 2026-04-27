import argparse
import json
import sys
from pathlib import Path

from metrics_engine import calculator as calc_mod
from metrics_engine import loader
from metrics_engine import metric_registry as registry_mod
from metrics_engine import output_builder
from metrics_engine import schema as schema_mod
from metrics_engine import validator as validator_mod
from metrics_engine.exporter import export
from metrics_engine.validator import ValidationReport


def _run_pipeline(input_path: str, schema_path: str, config_path: str):
    raw_df = loader.load(input_path)
    schema_config = schema_mod.load_schema(schema_path)
    norm_result = schema_mod.normalize(raw_df, schema_config)
    registry = registry_mod.load_metric_registry(config_path)
    report = validator_mod.validate(norm_result, registry)
    return norm_result, registry, report


def _print_report(report: ValidationReport) -> None:
    print(f"Status: {report.status}")
    if report.errors:
        print("Errors:")
        for e in report.errors:
            print(f"  - {e}")
    if report.warnings:
        print("Warnings:")
        for w in report.warnings:
            print(f"  - {w}")


def _write_report_json(report: ValidationReport, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "validation_report.json").write_text(
        json.dumps(
            {"status": report.status, "errors": report.errors, "warnings": report.warnings},
            indent=2,
        ),
        encoding="utf-8",
    )


def cmd_run(args) -> None:
    try:
        norm_result, registry, report = _run_pipeline(args.input, args.schema, args.config)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    _print_report(report)

    if getattr(args, "dry_run", False):
        if report.status == "failed":
            sys.exit(1)
        return

    if report.status == "failed":
        out_dir = Path(args.output)
        _write_report_json(report, out_dir)
        print(f"\nValidation failed. Report written to: {out_dir / 'validation_report.json'}")
        sys.exit(1)

    result_df = calc_mod.calculate(norm_result.df, registry)
    long_metrics = output_builder.build_long_metrics(result_df, registry)
    wide_metrics = output_builder.build_wide_metrics(long_metrics)
    metric_dict = output_builder.build_metric_dictionary(registry)

    out_dir = Path(args.output)
    export(long_metrics, wide_metrics, metric_dict, report, out_dir)

    print(f"\nOutput written to: {out_dir.resolve()}")
    for fname in ["long_metrics.csv", "wide_metrics.csv", "metric_dictionary.csv", "validation_report.json"]:
        print(f"  {fname}")


def cmd_validate(args) -> None:
    try:
        _, _, report = _run_pipeline(args.input, args.schema, args.config)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    _print_report(report)
    print("\nValidation complete. No metric files were written.")

    if report.status == "failed":
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="metrics_engine",
        description="Financial data metrics engine",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_p = subparsers.add_parser("run", help="Run the full pipeline and write output files")
    run_p.add_argument("--input", required=True, help="Input data file (CSV or Excel)")
    run_p.add_argument("--output", default="outputs/", help="Output directory (default: outputs/)")
    run_p.add_argument("--config", default="config/metrics.yaml", help="Metrics config (default: config/metrics.yaml)")
    run_p.add_argument("--schema", default="config/schema.yaml", help="Schema config (default: config/schema.yaml)")
    run_p.add_argument("--dry-run", dest="dry_run", action="store_true",
                       help="Validate only; do not write output files")

    val_p = subparsers.add_parser("validate", help="Validate input data without writing output")
    val_p.add_argument("--input", required=True, help="Input data file (CSV or Excel)")
    val_p.add_argument("--config", default="config/metrics.yaml")
    val_p.add_argument("--schema", default="config/schema.yaml")

    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args)
    elif args.command == "validate":
        cmd_validate(args)


if __name__ == "__main__":
    main()
