import html as _html

from intake_engine.models.profile import ProfileReport
from intake_engine.models.validation import ValidationReport

_CSS = """\
*{box-sizing:border-box}
body{font-family:-apple-system,system-ui,sans-serif;max-width:860px;margin:40px auto;padding:0 24px;color:#111;background:#fff;line-height:1.5}
h1{font-size:1.5rem;font-weight:700;margin:0 0 6px}
.meta{font-size:.85rem;color:#6b7280;margin-bottom:28px}
.badge{padding:2px 12px;border-radius:12px;font-size:.75rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em}
.pass{background:#d1fae5;color:#065f46}
.warn{background:#fef3c7;color:#92400e}
.fail{background:#fee2e2;color:#991b1b}
h2{font-size:.8rem;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:#6b7280;border-bottom:1px solid #e5e7eb;padding-bottom:5px;margin:32px 0 12px}
table{width:100%;border-collapse:collapse;font-size:.875rem}
th{text-align:left;padding:7px 12px;background:#f9fafb;color:#6b7280;font-weight:600;font-size:.78rem;text-transform:uppercase;letter-spacing:.04em;border-bottom:1px solid #e5e7eb}
td{padding:7px 12px;border-bottom:1px solid #f3f4f6;vertical-align:middle}
tr:last-child td{border-bottom:none}
.bar{display:inline-flex;align-items:center;gap:8px;white-space:nowrap}
.track{width:80px;height:7px;background:#e5e7eb;border-radius:4px;overflow:hidden;flex-shrink:0}
.fill{height:100%;border-radius:4px;display:block}
.ok{background:#22c55e}
.mid{background:#f59e0b}
.hi{background:#ef4444}
ul{margin:4px 0;padding-left:18px}
li+li{margin-top:4px}
.err{color:#991b1b;font-size:.875rem}
.wrn{color:#92400e;font-size:.875rem}"""


def build_html_report(
    file_name: str,
    profile: ProfileReport | None = None,
    validation: ValidationReport | None = None,
) -> str:
    """Build a self-contained HTML quality report from profile and/or validation data."""
    if not profile and not validation:
        return f"<html><body><p>No report data for {_html.escape(file_name)}</p></body></html>"

    e = _html.escape
    src = profile or validation
    ts_raw = src.run_timestamp  # type: ignore[union-attr]
    ts = ts_raw[:19].replace("T", " ") + " UTC"

    badge = (
        f'<span class="badge {validation.status}">{validation.status.upper()}</span>&nbsp; '
        if validation else ""
    )

    # Row / column stats — profile is richer; fall back to validation
    if profile:
        rows_loaded = profile.rows_loaded
        rows_output = profile.rows_output
        dupes = profile.duplicate_rows_removed
        ncols = profile.columns
        dup_rate = dupes / rows_loaded if rows_loaded > 0 else 0.0
    else:
        rows_loaded = validation.rows_loaded  # type: ignore[union-attr]
        rows_output = validation.row_count    # type: ignore[union-attr]
        dupes = rows_loaded - rows_output
        ncols = validation.columns            # type: ignore[union-attr]
        dup_rate = validation.duplicate_rate  # type: ignore[union-attr]

    # Null rates keyed on clean column names
    if validation:
        null_rates = dict(validation.null_summary)
    else:
        null_rates = {
            col: profile.null_counts[col] / rows_output if rows_output > 0 else 0.0  # type: ignore[union-attr]
            for col in profile.column_names  # type: ignore[union-attr]
        }

    # Merge warnings (deduplicated, validation first)
    all_warnings: list[str] = list(validation.warnings) if validation else []
    if profile:
        for w in profile.warnings:
            if w not in all_warnings:
                all_warnings.append(w)

    issues = validation.issues if validation else []

    # --- sections ---
    sections: list[str] = []

    sections.append(_section("Summary", _kv_table([
        ("Rows loaded",        f"{rows_loaded:,}"),
        ("Rows output",        f"{rows_output:,}"),
        ("Duplicates removed", f"{dupes:,}"),
        ("Columns",            str(ncols)),
        ("Duplicate rate",     f"{dup_rate:.1%}"),
    ])))

    if profile:
        rows = [
            f"<tr><td>{e(col)}</td>"
            f"<td>{e(profile.inferred_types.get(col, ''))}</td>"
            f"<td>{e(profile.semantic_types.get(col, ''))}</td></tr>"
            for col in profile.column_names
        ]
        sections.append(_section(
            "Column Types",
            f'<table><tr><th>Column</th><th>Inferred Type</th><th>Semantic Type</th></tr>{"".join(rows)}</table>',
        ))

    if null_rates:
        rows = [
            f"<tr><td>{e(col)}</td><td>{_bar(rate)}</td></tr>"
            for col, rate in null_rates.items()
        ]
        sections.append(_section(
            "Null Rates",
            f'<table><tr><th>Column</th><th>Null Rate</th></tr>{"".join(rows)}</table>',
        ))

    if profile and profile.columns_renamed:
        rows = [
            f"<tr><td>{e(old)}</td><td>{e(new)}</td></tr>"
            for old, new in profile.columns_renamed.items()
        ]
        sections.append(_section(
            "Columns Renamed",
            f'<table><tr><th>Original</th><th>Renamed To</th></tr>{"".join(rows)}</table>',
        ))

    if issues:
        items = "".join(f'<li class="err">{e(i)}</li>' for i in issues)
        sections.append(_section("Issues", f"<ul>{items}</ul>"))

    if all_warnings:
        items = "".join(f'<li class="wrn">{e(w)}</li>' for w in all_warnings)
        sections.append(_section("Warnings", f"<ul>{items}</ul>"))

    return (
        f'<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        f'<meta charset="utf-8">\n'
        f'<title>Data Quality Report — {e(file_name)}</title>\n'
        f'<style>\n{_CSS}\n</style>\n</head>\n<body>\n'
        f'<h1>Data Quality Report &mdash; {e(file_name)}</h1>\n'
        f'<div class="meta">{badge}Generated {e(ts)}</div>\n'
        f'{"".join(sections)}\n'
        f'</body>\n</html>'
    )


def _section(title: str, content: str) -> str:
    return f"<h2>{_html.escape(title)}</h2>\n{content}\n"


def _kv_table(rows: list[tuple[str, str]]) -> str:
    body = "".join(
        f"<tr><th>{_html.escape(k)}</th><td>{_html.escape(v)}</td></tr>"
        for k, v in rows
    )
    return f"<table>{body}</table>"


def _bar(rate: float) -> str:
    pct = round(rate * 100, 1)
    fill_cls = "hi" if pct > 30 else "mid" if pct > 5 else "ok"
    bar_w = min(int(pct), 100)
    return (
        f'<span class="bar">'
        f'<span class="track"><span class="fill {fill_cls}" style="width:{bar_w}%"></span></span>'
        f"{pct:.1f}%</span>"
    )
