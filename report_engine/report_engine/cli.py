from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from report_engine import loader, templates
from report_engine.html import render_html
from report_engine.insights import build_insights, has_period_data
from report_engine.renderer import render_markdown

_OUTPUT_FILES = ["report.md", "report.html", "summary.json", "insights.json"]


def _build_summary(data: loader.ReportData, template_name: str) -> dict:
    summary: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_dir": str(data.input_dir),
        "validation_status": data.validation_status,
        "error_count": len(data.validation_errors),
        "warning_count": len(data.validation_warnings),
        "template": template_name,
    }
    if not data.long_metrics.empty:
        df = data.long_metrics
        if "date" in df.columns:
            summary["date_range"] = {
                "min": str(df["date"].min()),
                "max": str(df["date"].max()),
            }
        if "metric_id" in df.columns:
            summary["metric_count"] = int(df["metric_id"].nunique())
        if "rollup_level" in df.columns:
            summary["rollup_levels"] = sorted(df["rollup_level"].dropna().unique().tolist())
    summary["generated_files"] = _OUTPUT_FILES
    return summary


def cmd_build(args) -> None:
    try:
        data = loader.load(args.input)
    except loader.LoaderError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    sections = templates.get_sections(args.template)

    insights = build_insights(data)
    insights_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "has_insights": bool(insights),
        "insights": insights,
    }

    (out / "report.md").write_text(render_markdown(data, sections=sections), encoding="utf-8")
    (out / "report.html").write_text(render_html(data, sections=sections), encoding="utf-8")
    (out / "summary.json").write_text(
        json.dumps(_build_summary(data, args.template), indent=2),
        encoding="utf-8",
    )
    (out / "insights.json").write_text(
        json.dumps(insights_payload, indent=2),
        encoding="utf-8",
    )

    print(f"Report written to: {out.resolve()}")
    for fname in _OUTPUT_FILES:
        print(f"  {fname}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="report_engine",
        description="Generate reports from Metrics Engine output",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_p = subparsers.add_parser("build", help="Build report from a metrics output directory")
    build_p.add_argument("--input", required=True, help="Metrics Engine output directory")
    build_p.add_argument(
        "--output",
        default="outputs/report",
        help="Output directory (default: outputs/report)",
    )
    build_p.add_argument(
        "--template",
        default=templates.DEFAULT_TEMPLATE,
        choices=templates.VALID_TEMPLATES,
        help=f"Report template (default: {templates.DEFAULT_TEMPLATE})",
    )

    args = parser.parse_args()
    if args.command == "build":
        cmd_build(args)


if __name__ == "__main__":
    main()
