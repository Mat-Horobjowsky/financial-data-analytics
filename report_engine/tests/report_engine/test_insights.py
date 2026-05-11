from pathlib import Path

import pandas as pd
import pytest

from report_engine.insights import build_insights, build_readiness_recommendations, has_period_data, snapshot_rows
from report_engine.loader import ReportData


def _make_data(rows, period_cols=False):
    base = {
        "rollup_level": [r[0] for r in rows],
        "date": [r[1] for r in rows],
        "metric_id": [r[2] for r in rows],
        "label": [r[3] for r in rows],
        "value": [r[4] for r in rows],
        "unit": [r[5] for r in rows],
    }
    if period_cols:
        base["prior_period_value"] = [r[6] for r in rows]
        base["period_change"] = [r[7] for r in rows]
        base["period_change_pct"] = [r[8] for r in rows]
    return ReportData(
        input_dir=Path("outputs/test"),
        validation_status="passed",
        validation_errors=[],
        validation_warnings=[],
        long_metrics=pd.DataFrame(base),
        wide_metrics=pd.DataFrame(),
        metric_dictionary=pd.DataFrame(),
    )


@pytest.fixture
def no_period_data():
    return _make_data([
        ("date_only", "2024-01-01", "total_revenue", "Total Revenue", 5900000.0, "USD"),
        ("date_only", "2024-02-01", "total_revenue", "Total Revenue", 6150000.0, "USD"),
    ])


@pytest.fixture
def period_data():
    return _make_data([
        ("date_only", "2024-01-01", "total_revenue", "Total Revenue", 5900000.0, "USD",
         float("nan"), float("nan"), float("nan")),
        ("date_only", "2024-02-01", "total_revenue", "Total Revenue", 6150000.0, "USD",
         5850000.0, 300000.0, 5.13),
    ], period_cols=True)


@pytest.fixture
def multi_metric_period_data():
    return _make_data([
        ("date_only", "2024-01-01", "total_revenue", "Total Revenue", 5900000.0, "USD",
         float("nan"), float("nan"), float("nan")),
        ("date_only", "2024-02-01", "total_revenue", "Total Revenue", 6150000.0, "USD",
         5850000.0, 300000.0, 5.13),
        ("date_only", "2024-01-01", "utilization_pct", "Utilization Rate", 81.2, "%",
         float("nan"), float("nan"), float("nan")),
        ("date_only", "2024-02-01", "utilization_pct", "Utilization Rate", 84.8, "%",
         81.2, 3.6, 4.43),
    ], period_cols=True)


@pytest.fixture
def empty_data():
    return ReportData(
        input_dir=Path("outputs/test"),
        validation_status="passed",
        validation_errors=[],
        validation_warnings=[],
        long_metrics=pd.DataFrame(),
        wide_metrics=pd.DataFrame(),
        metric_dictionary=pd.DataFrame(),
    )


# ── has_period_data ─────────────────────────────────────────────────────────────

def test_has_period_data_false_when_empty_df(empty_data):
    assert has_period_data(empty_data) is False


def test_has_period_data_false_when_no_column(no_period_data):
    assert has_period_data(no_period_data) is False


def test_has_period_data_true_when_column_present(period_data):
    assert has_period_data(period_data) is True


# ── snapshot_rows ───────────────────────────────────────────────────────────────

def test_snapshot_rows_empty_when_no_metrics(empty_data):
    assert snapshot_rows(empty_data) == []


def test_snapshot_rows_returns_one_row_per_metric(no_period_data):
    rows = snapshot_rows(no_period_data)
    assert len(rows) == 1


def test_snapshot_rows_returns_latest_date_per_metric(no_period_data):
    rows = snapshot_rows(no_period_data)
    assert rows[0]["date"] == "2024-02-01"


def test_snapshot_rows_single_period_returns_that_period():
    data = _make_data([
        ("date_only", "2024-01-01", "total_revenue", "Total Revenue", 5900000.0, "USD"),
    ])
    rows = snapshot_rows(data)
    assert len(rows) == 1
    assert rows[0]["date"] == "2024-01-01"


def test_snapshot_rows_excludes_non_date_only_rollup():
    data = _make_data([
        ("date_only", "2024-02-01", "total_revenue", "Total Revenue", 6150000.0, "USD"),
        ("date_region", "2024-02-01", "total_revenue", "Total Revenue", 3000000.0, "USD"),
    ])
    rows = snapshot_rows(data)
    assert len(rows) == 1
    assert rows[0]["value"] == 6150000.0


def test_snapshot_rows_includes_label_date_value_unit(no_period_data):
    rows = snapshot_rows(no_period_data)
    row = rows[0]
    assert "label" in row
    assert "date" in row
    assert "value" in row
    assert "unit" in row


def test_snapshot_rows_sorted_by_label(multi_metric_period_data):
    rows = snapshot_rows(multi_metric_period_data)
    labels = [r["label"] for r in rows]
    assert labels == sorted(labels)


def test_snapshot_rows_multiple_metrics_one_row_each(multi_metric_period_data):
    rows = snapshot_rows(multi_metric_period_data)
    assert len(rows) == 2


def test_snapshot_rows_no_rollup_level_column():
    data = ReportData(
        input_dir=Path("outputs/test"),
        validation_status="passed",
        validation_errors=[],
        validation_warnings=[],
        long_metrics=pd.DataFrame({
            "date": ["2024-01-01", "2024-02-01"],
            "metric_id": ["total_revenue", "total_revenue"],
            "label": ["Total Revenue", "Total Revenue"],
            "value": [5900000.0, 6150000.0],
            "unit": ["USD", "USD"],
        }),
        wide_metrics=pd.DataFrame(),
        metric_dictionary=pd.DataFrame(),
    )
    rows = snapshot_rows(data)
    assert len(rows) == 1
    assert rows[0]["date"] == "2024-02-01"


# ── build_insights ──────────────────────────────────────────────────────────────

def test_build_insights_empty_when_no_period_column(no_period_data):
    assert build_insights(no_period_data) == []


def test_build_insights_empty_when_no_metrics(empty_data):
    assert build_insights(empty_data) == []


def test_build_insights_skips_nan_rows(period_data):
    # first period row has NaN period_change_pct — only one insight from second period
    insights = build_insights(period_data)
    assert len(insights) == 1


def test_build_insights_positive_pct_direction_up(period_data):
    insights = build_insights(period_data)
    assert insights[0]["direction"] == "up"


def test_build_insights_positive_pct_text_says_increased(period_data):
    insights = build_insights(period_data)
    assert "increased" in insights[0]["text"]


def test_build_insights_negative_pct_direction_down():
    data = _make_data([
        ("date_only", "2024-01-01", "total_revenue", "Total Revenue", 6000000.0, "USD",
         float("nan"), float("nan"), float("nan")),
        ("date_only", "2024-02-01", "total_revenue", "Total Revenue", 5700000.0, "USD",
         6000000.0, -300000.0, -5.0),
    ], period_cols=True)
    insights = build_insights(data)
    assert insights[0]["direction"] == "down"


def test_build_insights_negative_pct_text_says_decreased():
    data = _make_data([
        ("date_only", "2024-01-01", "total_revenue", "Total Revenue", 6000000.0, "USD",
         float("nan"), float("nan"), float("nan")),
        ("date_only", "2024-02-01", "total_revenue", "Total Revenue", 5700000.0, "USD",
         6000000.0, -300000.0, -5.0),
    ], period_cols=True)
    insights = build_insights(data)
    assert "decreased" in insights[0]["text"]


def test_build_insights_zero_pct_direction_flat():
    data = _make_data([
        ("date_only", "2024-01-01", "total_revenue", "Total Revenue", 6000000.0, "USD",
         float("nan"), float("nan"), float("nan")),
        ("date_only", "2024-02-01", "total_revenue", "Total Revenue", 6000000.0, "USD",
         6000000.0, 0.0, 0.0),
    ], period_cols=True)
    insights = build_insights(data)
    assert insights[0]["direction"] == "flat"


def test_build_insights_zero_pct_text_says_remained_flat():
    data = _make_data([
        ("date_only", "2024-01-01", "total_revenue", "Total Revenue", 6000000.0, "USD",
         float("nan"), float("nan"), float("nan")),
        ("date_only", "2024-02-01", "total_revenue", "Total Revenue", 6000000.0, "USD",
         6000000.0, 0.0, 0.0),
    ], period_cols=True)
    insights = build_insights(data)
    assert "remained flat" in insights[0]["text"]


def test_build_insights_text_uses_label_not_metric_id(period_data):
    insights = build_insights(period_data)
    assert "Total Revenue" in insights[0]["text"]
    assert "total_revenue" not in insights[0]["text"]


def test_build_insights_text_includes_formatted_pct(period_data):
    insights = build_insights(period_data)
    # format_metric_value(5.13, "%") → "5.13%"
    assert "5.13%" in insights[0]["text"]


def test_build_insights_text_includes_vs_prior_period(period_data):
    insights = build_insights(period_data)
    assert "vs prior period" in insights[0]["text"]


def test_build_insights_schema_has_required_keys(period_data):
    insights = build_insights(period_data)
    required = {"metric_id", "label", "date", "period_change_pct", "direction", "text"}
    assert required.issubset(set(insights[0].keys()))


def test_build_insights_multiple_metrics_sorted_by_metric_id(multi_metric_period_data):
    insights = build_insights(multi_metric_period_data)
    ids = [i["metric_id"] for i in insights]
    assert ids == sorted(ids)


def test_build_insights_multiple_metrics_count(multi_metric_period_data):
    insights = build_insights(multi_metric_period_data)
    assert len(insights) == 2


def test_build_insights_uses_latest_period_per_metric(multi_metric_period_data):
    insights = build_insights(multi_metric_period_data)
    for insight in insights:
        assert insight["date"] == "2024-02-01"


# ── build_readiness_recommendations ────────────────────────────────────────────

def _make_readiness_data(
    completion_pct=None,
    gap_count=None,
    critical_count=None,
    requirement_count=None,
    category_rows=None,
):
    """Build ReportData for readiness recommendation tests.

    category_rows: list of (category_name, completion_pct, gap_count, critical_count, req_count).
    Any individual value can be None to omit that metric for that category.
    """
    date_only = []
    if completion_pct is not None:
        date_only.append(("date_only", "2025-01-01", "readiness_completion_pct", "Readiness Completion %", float(completion_pct), "%", None))
    if gap_count is not None:
        date_only.append(("date_only", "2025-01-01", "open_gap_count", "Open Gap Count", float(gap_count), "gaps", None))
    if critical_count is not None:
        date_only.append(("date_only", "2025-01-01", "critical_item_count", "Critical Item Count", float(critical_count), "items", None))
    if requirement_count is not None:
        date_only.append(("date_only", "2025-01-01", "total_requirement_count", "Total Requirement Count", float(requirement_count), "requirements", None))

    cat_rows_flat = []
    if category_rows:
        for (cat, pct, gaps, crits, reqs) in category_rows:
            if pct is not None:
                cat_rows_flat.append(("date_category", "2025-01-01", "readiness_completion_pct", "Readiness Completion %", float(pct), "%", cat))
            if gaps is not None:
                cat_rows_flat.append(("date_category", "2025-01-01", "open_gap_count", "Open Gap Count", float(gaps), "gaps", cat))
            if crits is not None:
                cat_rows_flat.append(("date_category", "2025-01-01", "critical_item_count", "Critical Item Count", float(crits), "items", cat))
            if reqs is not None:
                cat_rows_flat.append(("date_category", "2025-01-01", "total_requirement_count", "Total Requirement Count", float(reqs), "requirements", cat))

    all_rows = date_only + cat_rows_flat
    if not all_rows:
        return ReportData(
            input_dir=Path("outputs/test"),
            validation_status="passed",
            validation_errors=[],
            validation_warnings=[],
            long_metrics=pd.DataFrame(),
            wide_metrics=pd.DataFrame(),
            metric_dictionary=pd.DataFrame(),
        )

    df_data = {
        "rollup_level": [r[0] for r in all_rows],
        "date": [r[1] for r in all_rows],
        "metric_id": [r[2] for r in all_rows],
        "label": [r[3] for r in all_rows],
        "value": [r[4] for r in all_rows],
        "unit": [r[5] for r in all_rows],
    }
    if cat_rows_flat:
        df_data["category"] = [r[6] for r in all_rows]

    return ReportData(
        input_dir=Path("outputs/test"),
        validation_status="passed",
        validation_errors=[],
        validation_warnings=[],
        long_metrics=pd.DataFrame(df_data),
        wide_metrics=pd.DataFrame(),
        metric_dictionary=pd.DataFrame(),
    )


# ── Fallback when no readiness data ─────────────────────────────────────────────

def test_readiness_recs_fallback_when_no_readiness_data(empty_data):
    recs = build_readiness_recommendations(empty_data)
    assert len(recs) == 1
    assert "Review" in recs[0]["recommendation"]


def test_readiness_recs_fallback_has_expected_schema(empty_data):
    recs = build_readiness_recommendations(empty_data)
    required = {"priority", "category", "severity", "recommendation", "rationale"}
    assert required == set(recs[0].keys())


def test_readiness_recs_fallback_when_non_readiness_metrics_only(no_period_data):
    recs = build_readiness_recommendations(no_period_data)
    assert len(recs) == 1
    assert "Review" in recs[0]["recommendation"]


# ── Critical blocker recommendation ─────────────────────────────────────────────

def test_readiness_recs_critical_when_count_above_zero():
    data = _make_readiness_data(completion_pct=50, critical_count=3)
    recs = build_readiness_recommendations(data)
    assert any(r["severity"] == "critical" for r in recs)


def test_readiness_recs_critical_recommendation_contains_count():
    data = _make_readiness_data(completion_pct=50, critical_count=3)
    recs = build_readiness_recommendations(data)
    crit_rec = next(r for r in recs if r["severity"] == "critical")
    assert "3" in crit_rec["recommendation"]


def test_readiness_recs_critical_recommendation_mentions_blocker():
    data = _make_readiness_data(completion_pct=50, critical_count=3)
    recs = build_readiness_recommendations(data)
    crit_rec = next(r for r in recs if r["severity"] == "critical")
    assert "blocker" in crit_rec["recommendation"].lower()


def test_readiness_recs_critical_is_priority_one():
    data = _make_readiness_data(completion_pct=50, critical_count=2)
    recs = build_readiness_recommendations(data)
    crit_rec = next(r for r in recs if r["severity"] == "critical")
    assert crit_rec["priority"] == 1


def test_readiness_recs_no_critical_when_count_is_zero():
    data = _make_readiness_data(completion_pct=70, critical_count=0)
    recs = build_readiness_recommendations(data)
    assert not any(r["severity"] == "critical" for r in recs)


# ── Highest open-gap category recommendation ────────────────────────────────────

def test_readiness_recs_highest_gap_category_gets_recommendation():
    data = _make_readiness_data(
        completion_pct=70,
        gap_count=6,
        category_rows=[
            ("power", 75.0, 3, 1, 4),
            ("commercial", 50.0, 1, 0, 2),
            ("fiber", 66.7, 2, 0, 3),
        ],
    )
    recs = build_readiness_recommendations(data)
    assert any(r.get("category") == "power" for r in recs)


def test_readiness_recs_highest_gap_category_uses_known_category_text():
    data = _make_readiness_data(
        completion_pct=70,
        gap_count=5,
        category_rows=[
            ("commercial", 50.0, 3, 0, 4),
            ("power", 75.0, 1, 0, 4),
        ],
    )
    recs = build_readiness_recommendations(data)
    gap_rec = next((r for r in recs if r.get("category") == "commercial" and r["severity"] == "high"), None)
    assert gap_rec is not None
    assert "commercial" in gap_rec["recommendation"].lower()


def test_readiness_recs_highest_gap_category_uses_generic_text_for_unknown():
    data = _make_readiness_data(
        completion_pct=70,
        gap_count=5,
        category_rows=[
            ("rooftop", 50.0, 4, 0, 8),
            ("power", 75.0, 1, 0, 4),
        ],
    )
    recs = build_readiness_recommendations(data)
    gap_rec = next((r for r in recs if r.get("category") == "rooftop"), None)
    assert gap_rec is not None
    assert "rooftop" in gap_rec["recommendation"].lower()


def test_readiness_recs_highest_gap_category_severity_is_high():
    data = _make_readiness_data(
        completion_pct=70,
        gap_count=5,
        category_rows=[
            ("permitting", 40.0, 3, 0, 5),
            ("fiber", 60.0, 1, 0, 3),
        ],
    )
    recs = build_readiness_recommendations(data)
    high_recs = [r for r in recs if r.get("category") == "permitting" and r["severity"] == "high"]
    assert high_recs


def test_readiness_recs_no_gap_rec_when_all_gaps_zero():
    data = _make_readiness_data(
        completion_pct=80,
        critical_count=0,
        category_rows=[
            ("power", 100.0, 0, 0, 4),
            ("fiber", 100.0, 0, 0, 3),
        ],
    )
    recs = build_readiness_recommendations(data)
    assert not any(r["severity"] == "high" and r.get("rationale", "").endswith(").")
                   and "open gap" in r.get("rationale", "") for r in recs)


# ── Lowest readiness category recommendation ────────────────────────────────────

def test_readiness_recs_lowest_completion_category_gets_recommendation():
    data = _make_readiness_data(
        completion_pct=55,
        category_rows=[
            ("capital", 33.3, 2, 0, 3),
            ("power", 75.0, 1, 0, 4),
            ("fiber", 66.7, 1, 0, 3),
        ],
    )
    recs = build_readiness_recommendations(data)
    assert any(r.get("category") == "capital" for r in recs)


def test_readiness_recs_lowest_completion_uses_known_category_text():
    data = _make_readiness_data(
        completion_pct=50,
        category_rows=[
            ("site_control", 25.0, 2, 0, 4),
            ("power", 75.0, 1, 0, 4),
        ],
    )
    recs = build_readiness_recommendations(data)
    low_rec = next((r for r in recs if r.get("category") == "site_control"), None)
    assert low_rec is not None
    assert "site" in low_rec["recommendation"].lower()


def test_readiness_recs_lowest_completion_severity_is_high():
    data = _make_readiness_data(
        completion_pct=50,
        category_rows=[
            ("fiber", 33.3, 2, 0, 3),
            ("commercial", 66.7, 1, 0, 3),
        ],
    )
    recs = build_readiness_recommendations(data)
    low_rec = next((r for r in recs if r.get("category") == "fiber"), None)
    assert low_rec is not None
    assert low_rec["severity"] == "high"


# ── Low-readiness hold recommendation ──────────────────────────────────────────

def test_readiness_recs_hold_when_pct_below_60():
    data = _make_readiness_data(completion_pct=55)
    recs = build_readiness_recommendations(data)
    assert any("Hold" in r["recommendation"] for r in recs)


def test_readiness_recs_hold_recommendation_mentions_rfp():
    data = _make_readiness_data(completion_pct=40)
    recs = build_readiness_recommendations(data)
    assert any("RFP" in r["recommendation"] for r in recs)


def test_readiness_recs_hold_severity_is_medium():
    data = _make_readiness_data(completion_pct=50)
    recs = build_readiness_recommendations(data)
    hold_rec = next((r for r in recs if "RFP" in r["recommendation"]), None)
    assert hold_rec is not None
    assert hold_rec["severity"] == "medium"


def test_readiness_recs_no_hold_when_pct_at_60():
    data = _make_readiness_data(completion_pct=60, critical_count=0)
    recs = build_readiness_recommendations(data)
    assert not any("RFP" in r["recommendation"] for r in recs)


def test_readiness_recs_no_hold_when_pct_above_60():
    data = _make_readiness_data(completion_pct=70, critical_count=0)
    recs = build_readiness_recommendations(data)
    assert not any("RFP" in r["recommendation"] for r in recs)


# ── High-readiness / zero-critical proceed recommendation ───────────────────────

def test_readiness_recs_proceed_when_pct_above_80_and_no_criticals():
    data = _make_readiness_data(completion_pct=85, critical_count=0)
    recs = build_readiness_recommendations(data)
    assert any("market" in r["recommendation"].lower() for r in recs)


def test_readiness_recs_proceed_recommendation_mentions_investor():
    data = _make_readiness_data(completion_pct=90, critical_count=0)
    recs = build_readiness_recommendations(data)
    assert any("investor" in r["recommendation"].lower() for r in recs)


def test_readiness_recs_proceed_severity_is_low():
    data = _make_readiness_data(completion_pct=90, critical_count=0)
    recs = build_readiness_recommendations(data)
    proc_rec = next((r for r in recs if "market" in r["recommendation"].lower()), None)
    assert proc_rec is not None
    assert proc_rec["severity"] == "low"


def test_readiness_recs_no_proceed_when_criticals_present():
    data = _make_readiness_data(completion_pct=90, critical_count=2)
    recs = build_readiness_recommendations(data)
    assert not any("market-facing" in r["recommendation"].lower() for r in recs)


def test_readiness_recs_no_proceed_when_pct_below_80():
    data = _make_readiness_data(completion_pct=75, critical_count=0)
    recs = build_readiness_recommendations(data)
    assert not any("market-facing" in r["recommendation"].lower() for r in recs)


def test_readiness_recs_proceed_when_pct_exactly_80_and_no_criticals():
    data = _make_readiness_data(completion_pct=80, critical_count=0)
    recs = build_readiness_recommendations(data)
    assert any("market" in r["recommendation"].lower() for r in recs)


# ── Schema and priority ordering ────────────────────────────────────────────────

def test_readiness_recs_all_have_required_fields():
    data = _make_readiness_data(completion_pct=50, critical_count=2, gap_count=5)
    recs = build_readiness_recommendations(data)
    required = {"priority", "category", "severity", "recommendation", "rationale"}
    for rec in recs:
        assert required == set(rec.keys())


def test_readiness_recs_priorities_are_sequential():
    data = _make_readiness_data(completion_pct=50, critical_count=2, gap_count=5)
    recs = build_readiness_recommendations(data)
    priorities = [r["priority"] for r in recs]
    assert priorities == list(range(1, len(recs) + 1))


# ── Existing generic templates unaffected ───────────────────────────────────────

def test_generic_templates_full_report_sections_unchanged():
    from report_engine.templates import get_sections
    assert get_sections("full_report") == [
        "header", "validation", "kpi_snapshot", "key_insights", "metrics_summary", "metric_dictionary",
    ]


def test_generic_templates_executive_summary_sections_unchanged():
    from report_engine.templates import get_sections
    assert get_sections("executive_summary") == [
        "header", "validation", "kpi_snapshot", "key_insights",
    ]


def test_generic_templates_metrics_detail_sections_unchanged():
    from report_engine.templates import get_sections
    assert get_sections("metrics_detail") == [
        "header", "validation", "metrics_summary", "metric_dictionary",
    ]


def test_build_readiness_recommendations_does_not_affect_build_insights(period_data):
    insights_before = build_insights(period_data)
    build_readiness_recommendations(period_data)
    insights_after = build_insights(period_data)
    assert insights_before == insights_after
