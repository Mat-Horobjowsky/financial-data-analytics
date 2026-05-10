from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="visuals-engine",
        description="Render analytics.duckdb into a static business-ready dashboard.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="Build a dashboard from an analytics store")
    build.add_argument("--store", required=True, help="Path to analytics.duckdb")
    build.add_argument("--spec", required=True, help="Path to dashboard spec YAML")
    build.add_argument("--output", required=True, help="Output directory path")

    export_pbi = subparsers.add_parser(
        "export-powerbi",
        help="Export Power BI-ready CSVs from analytics.duckdb",
    )
    export_pbi.add_argument("--store", required=True, help="Path to analytics.duckdb")
    export_pbi.add_argument("--output", required=True, help="Output directory for CSV files")
    export_pbi.add_argument(
        "--client-context",
        dest="client_context",
        default=None,
        help="Optional path to client_context.csv; copied into the output directory when provided",
    )

    args = parser.parse_args()

    if args.command == "build":
        _run_build(args.store, args.spec, args.output)
    elif args.command == "export-powerbi":
        _run_export_powerbi(args.store, args.output, getattr(args, "client_context", None))


def _run_build(store_path: str, spec_path: str, output_dir: str) -> None:
    import yaml
    from . import loader, renderer

    spec_file = Path(spec_path)
    if not spec_file.exists():
        print(f"Error: spec file not found: {spec_path}", file=sys.stderr)
        sys.exit(1)

    with open(spec_file, encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    try:
        con = loader.connect(store_path)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        data = loader.load_all(con, spec)
    finally:
        con.close()

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    template_path = Path(__file__).parent / "templates" / "readiness_dashboard.html"
    html_content = renderer.render_html(template_path, spec, data)
    summary = renderer.render_summary(spec, data, store_path, spec_path)

    html_file = output_path / "readiness_dashboard.html"
    json_file = output_path / "visuals_summary.json"

    html_file.write_text(html_content, encoding="utf-8")
    json_file.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    print(f"Dashboard: {html_file}")
    print(f"Summary:   {json_file}")


def _run_export_powerbi(store_path: str, output_dir: str, client_context: str | None = None) -> None:
    from pathlib import Path as _Path
    from . import loader, exporter

    if client_context is not None and not _Path(client_context).exists():
        print(f"Error: client_context file not found: {client_context}", file=sys.stderr)
        sys.exit(1)

    try:
        con = loader.connect(store_path)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    ctx_path = _Path(client_context) if client_context is not None else None
    try:
        files = exporter.export_powerbi(con, _Path(output_dir), client_context_path=ctx_path)
    finally:
        con.close()

    for f in files:
        print(f"  {f}")
    print(f"\nPower BI export complete: {output_dir}")


if __name__ == "__main__":
    main()
