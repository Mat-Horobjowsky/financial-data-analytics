from __future__ import annotations

import argparse
import sys
from pathlib import Path

from report_engine.templates import DEFAULT_TEMPLATE, VALID_TEMPLATES

from .runner import run_pipeline
from .stages import StageContext
from .summary import build_pipeline_summary, write_summary


def cmd_run(args) -> None:
    input_file = Path(args.input)
    if not input_file.exists():
        print(f"Error: input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    metrics_config = Path(args.metrics_config) if args.metrics_config else None
    schema_config = Path(args.schema_config) if args.schema_config else None
    client_context = Path(args.client_context) if args.client_context else None

    if metrics_config and not metrics_config.exists():
        print(f"Error: metrics config not found: {metrics_config}", file=sys.stderr)
        sys.exit(1)
    if schema_config and not schema_config.exists():
        print(f"Error: schema config not found: {schema_config}", file=sys.stderr)
        sys.exit(1)
    if client_context and not client_context.exists():
        print(f"Error: client context file not found: {client_context}", file=sys.stderr)
        sys.exit(1)

    ctx = StageContext(
        input_file=input_file,
        output_root=Path(args.output),
        with_time=args.with_time,
        template=args.template,
        results={},
        with_store=args.with_store or args.with_visuals or args.with_powerbi_export,
        with_visuals=args.with_visuals,
        with_powerbi_export=args.with_powerbi_export,
        metrics_config=metrics_config,
        schema_config=schema_config,
        sheet=args.sheet,
        client_context_path=client_context,
    )

    results = run_pipeline(ctx)
    summary = build_pipeline_summary(ctx, results)
    summary_path = write_summary(summary, ctx.output_root)

    for name, stage_data in summary["stages"].items():
        print(f"  {name}: {stage_data['status']}")

    print(f"\npipeline_summary.json -> {summary_path}")
    overall = summary["status"]
    print(f"\nPipeline: {overall.upper()}")

    if overall != "success":
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="analytics-pipeline",
        description="Run the full Intake → Metrics → Report pipeline",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_p = subparsers.add_parser("run", help="Run all pipeline stages")
    run_p.add_argument("--input", required=True, help="Raw input file (CSV or XLSX)")
    run_p.add_argument(
        "--output",
        default="outputs/pipeline",
        help="Pipeline output directory (default: outputs/pipeline)",
    )
    run_p.add_argument(
        "--with-time",
        dest="with_time",
        action="store_true",
        help="Enable prior-period time analysis in Metrics Engine",
    )
    run_p.add_argument(
        "--template",
        default=DEFAULT_TEMPLATE,
        choices=VALID_TEMPLATES,
        help=f"Report template (default: {DEFAULT_TEMPLATE})",
    )
    run_p.add_argument(
        "--with-store",
        dest="with_store",
        action="store_true",
        help="Run the analytics_store stage after report (creates store/analytics.duckdb)",
    )
    run_p.add_argument(
        "--with-visuals",
        dest="with_visuals",
        action="store_true",
        help="Run the visuals_engine stage after store (creates readiness_dashboard.html); implies --with-store",
    )
    run_p.add_argument(
        "--with-powerbi-export",
        dest="with_powerbi_export",
        action="store_true",
        help="Run the Power BI CSV export stage after store; implies --with-store",
    )
    run_p.add_argument(
        "--metrics-config",
        dest="metrics_config",
        default=None,
        help="Custom Metrics Engine config YAML (default: metrics_engine/config/metrics.yaml)",
    )
    run_p.add_argument(
        "--schema-config",
        dest="schema_config",
        default=None,
        help="Custom Metrics Engine schema YAML (default: metrics_engine/config/schema.yaml)",
    )
    run_p.add_argument(
        "--sheet",
        default=None,
        help="Excel sheet name to pass to Intake Engine (optional, for XLSX files with multiple sheets)",
    )
    run_p.add_argument(
        "--client-context",
        dest="client_context",
        default=None,
        help="Optional path to client_context.csv; copied into powerbi/ when --with-powerbi-export is used",
    )

    args = parser.parse_args()
    if args.command == "run":
        cmd_run(args)


if __name__ == "__main__":
    main()
