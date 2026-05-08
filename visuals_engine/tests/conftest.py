import pytest
import duckdb
from pathlib import Path


@pytest.fixture
def sample_store(tmp_path) -> str:
    """Minimal analytics.duckdb with date_only and date_category rows."""
    db_path = tmp_path / "test_analytics.duckdb"
    con = duckdb.connect(str(db_path))

    con.execute("""
        CREATE TABLE long_metrics (
            rollup_level VARCHAR, date VARCHAR, category VARCHAR, market VARCHAR,
            metric_id VARCHAR, label VARCHAR, value DOUBLE, unit VARCHAR
        )
    """)
    con.execute("""
        INSERT INTO long_metrics VALUES
        ('date_only', '2025-01-15', NULL, NULL, 'readiness_completion_pct', 'Readiness Completion %', 50.0, '%'),
        ('date_only', '2025-01-15', NULL, NULL, 'total_requirement_count', 'Total Requirement Count', 20.0, 'requirements'),
        ('date_only', '2025-01-15', NULL, NULL, 'open_gap_count', 'Open Gap Count', 10.0, 'gaps'),
        ('date_only', '2025-01-15', NULL, NULL, 'critical_item_count', 'Critical Item Count', 4.0, 'items'),
        ('date_category', '2025-01-15', 'capital', NULL, 'readiness_completion_pct', 'Readiness Completion %', 33.3, '%'),
        ('date_category', '2025-01-15', 'capital', NULL, 'open_gap_count', 'Open Gap Count', 2.0, 'gaps'),
        ('date_category', '2025-01-15', 'commercial', NULL, 'readiness_completion_pct', 'Readiness Completion %', 66.7, '%'),
        ('date_category', '2025-01-15', 'commercial', NULL, 'open_gap_count', 'Open Gap Count', 1.0, 'gaps')
    """)

    con.execute("""
        CREATE TABLE metric_dictionary (
            id VARCHAR, label VARCHAR, type VARCHAR, unit VARCHAR,
            decimals BIGINT, description VARCHAR
        )
    """)
    con.execute("""
        INSERT INTO metric_dictionary VALUES
        ('readiness_completion_pct', 'Readiness Completion %', 'completion_pct', '%', 1, 'Percentage of requirements marked complete'),
        ('total_requirement_count', 'Total Requirement Count', 'count', 'requirements', 0, 'Total number of requirements'),
        ('open_gap_count', 'Open Gap Count', 'conditional_count', 'gaps', 0, 'Requirements not yet complete'),
        ('critical_item_count', 'Critical Item Count', 'conditional_count', 'items', 0, 'Requirements marked critical')
    """)

    con.execute("""
        CREATE TABLE metrics_validation_summary (
            status VARCHAR, error_count BIGINT, warning_count BIGINT
        )
    """)
    con.execute("INSERT INTO metrics_validation_summary VALUES ('passed_with_warnings', 0, 5)")

    con.close()
    return str(db_path)


@pytest.fixture
def sample_store_no_breakdowns(tmp_path) -> str:
    """Store with only date_only rows — no category or market breakdowns."""
    db_path = tmp_path / "test_no_breakdowns.duckdb"
    con = duckdb.connect(str(db_path))

    con.execute("""
        CREATE TABLE long_metrics (
            rollup_level VARCHAR, date VARCHAR, category VARCHAR, market VARCHAR,
            metric_id VARCHAR, label VARCHAR, value DOUBLE, unit VARCHAR
        )
    """)
    con.execute("""
        INSERT INTO long_metrics VALUES
        ('date_only', '2025-01-15', NULL, NULL, 'readiness_completion_pct', 'Readiness Completion %', 50.0, '%'),
        ('date_only', '2025-01-15', NULL, NULL, 'total_requirement_count', 'Total Requirement Count', 20.0, 'requirements'),
        ('date_only', '2025-01-15', NULL, NULL, 'open_gap_count', 'Open Gap Count', 10.0, 'gaps'),
        ('date_only', '2025-01-15', NULL, NULL, 'critical_item_count', 'Critical Item Count', 4.0, 'items')
    """)

    con.execute("""
        CREATE TABLE metric_dictionary (
            id VARCHAR, label VARCHAR, type VARCHAR, unit VARCHAR,
            decimals BIGINT, description VARCHAR
        )
    """)

    con.execute("""
        CREATE TABLE metrics_validation_summary (
            status VARCHAR, error_count BIGINT, warning_count BIGINT
        )
    """)

    con.close()
    return str(db_path)


@pytest.fixture
def spec_path() -> Path:
    return Path(__file__).parent.parent / "visuals_engine" / "specs" / "readiness_dashboard.yaml"


@pytest.fixture
def sample_spec() -> dict:
    return {
        "dashboard": {
            "title": "Test Dashboard",
            "description": "Test description",
            "store_tables": {
                "metrics": "long_metrics",
                "dictionary": "metric_dictionary",
                "validation": "metrics_validation_summary",
            },
        },
        "sections": [
            {
                "type": "kpi_cards",
                "title": "Key Metrics",
                "rollup_level": "date_only",
                "metrics": [
                    "readiness_completion_pct",
                    "total_requirement_count",
                    "open_gap_count",
                    "critical_item_count",
                ],
            },
            {
                "type": "category_breakdown",
                "title": "By Category",
                "rollup_level": "date_category",
                "segment_column": "category",
                "metrics": ["readiness_completion_pct", "open_gap_count"],
                "optional": True,
            },
            {
                "type": "market_breakdown",
                "title": "By Market",
                "rollup_level": "date_market",
                "segment_column": "market",
                "metrics": ["readiness_completion_pct", "open_gap_count"],
                "optional": True,
            },
        ],
    }
