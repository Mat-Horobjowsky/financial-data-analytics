from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .loader import LoaderError, load_metrics, load_report
from .writer import build_store


def cmd_build(args) -> None:
    metrics_dir = Path(args.metrics)
    if not metrics_dir.exists():
        print(f"Error: metrics directory not found: {metrics_dir}", file=sys.stderr)
        sys.exit(1)

    try:
        metrics_data = load_metrics(metrics_dir)
    except LoaderError as exc:
        print(f"Error loading metrics: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        report_data = load_report(args.report)
    except LoaderError as exc:
        print(f"Error loading report: {exc}", file=sys.stderr)
        sys.exit(1)

    db_path = Path(args.output)
    created = build_store(metrics_data, report_data, db_path)

    tables = [n for n in created if not n.startswith("v_")]
    views = [n for n in created if n.startswith("v_")]
    print(f"Store written to: {db_path.resolve()}")
    print(f"  Tables ({len(tables)}): {', '.join(tables)}")
    print(f"  Views  ({len(views)}): {', '.join(views)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="analytics-store",
        description="Load Metrics Engine and Report Engine outputs into a DuckDB analytics store",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_p = subparsers.add_parser("build", help="Build the analytics store from metrics and report outputs")
    build_p.add_argument("--metrics", required=True, help="Metrics Engine output directory")
    build_p.add_argument("--report", default=None, help="Report Engine output directory (optional)")
    build_p.add_argument(
        "--output",
        default="outputs/store.duckdb",
        help="Output DuckDB file path (default: outputs/store.duckdb)",
    )

    args = parser.parse_args()
    if args.command == "build":
        cmd_build(args)


if __name__ == "__main__":
    main()
