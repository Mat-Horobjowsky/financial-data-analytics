from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import openpyxl

from .builder import (
    _read_client_export,
    build_powerbi_export,
    write_client_context,
    write_client_export_sheet,
    write_powerbi_export,
)
from .demo_context import apply_demo_context


def cmd_build(args) -> None:
    workbook_path = Path(args.workbook)
    if not workbook_path.exists():
        print(f"Error: workbook not found: {workbook_path}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output)

    if args.in_place:
        output_path = workbook_path
    else:
        if output_path.resolve() == workbook_path.resolve():
            print(
                "Error: --output is the same path as --workbook. "
                "Use --in-place to overwrite the source.",
                file=sys.stderr,
            )
            sys.exit(1)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(workbook_path), str(output_path))

    context_path = (
        Path(args.client_context_output)
        if args.client_context_output
        else output_path.parent / "client_context.csv"
    )

    if args.demo_context:
        try:
            wb_src = openpyxl.load_workbook(str(workbook_path), data_only=True)
            src_client = _read_client_export(wb_src)
            demo_client = apply_demo_context(src_client)
            write_client_export_sheet(output_path, demo_client)
            rows = build_powerbi_export(output_path)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        write_powerbi_export(output_path, rows)
        write_client_context(demo_client, context_path)
    else:
        try:
            rows = build_powerbi_export(workbook_path)
            wb = openpyxl.load_workbook(str(workbook_path), data_only=True)
            client = _read_client_export(wb)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        write_powerbi_export(output_path, rows)
        write_client_context(client, context_path)

    print(f"Generated {len(rows)} rows in PowerBI_Export")
    print(f"Output:         {output_path}")
    print(f"Client context: {context_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="readiness-workbook",
        description="Readiness workbook builder — generates PowerBI_Export and client_context.csv",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_p = subparsers.add_parser(
        "build",
        help="Build PowerBI_Export from Requirement_Map + Client_Export",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Read Requirement_Map + Client_Export sheets from a client intake workbook,\n"
            "resolve each requirement's status from intake field answers, and write:\n"
            "  - a flat PowerBI_Export sheet (one row per requirement)\n"
            "  - a client_context.csv sidecar (project metadata for Power BI template)"
        ),
    )
    build_p.add_argument("--workbook", required=True, help="Source workbook (.xlsx)")
    build_p.add_argument(
        "--output",
        required=True,
        help="Output workbook path (new file; source is never modified by default)",
    )
    build_p.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite source workbook in place (unsafe; use with caution)",
    )
    build_p.add_argument(
        "--client-context-output",
        dest="client_context_output",
        default=None,
        help=(
            "Path for the client_context.csv sidecar "
            "(default: client_context.csv in the same directory as --output)"
        ),
    )
    build_p.add_argument(
        "--demo-context",
        dest="demo_context",
        action="store_true",
        help=(
            "Enrich the generated workbook's Client_Export with realistic demo metadata "
            "and generate a richer client_context.csv. Source workbook is never modified."
        ),
    )

    args = parser.parse_args()
    if args.command == "build":
        cmd_build(args)


if __name__ == "__main__":
    main()
