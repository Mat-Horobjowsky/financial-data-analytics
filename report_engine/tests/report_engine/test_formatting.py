import math

import pytest

from report_engine.formatting import format_metric_value


def test_format_usd_value_adds_dollar_sign_and_commas():
    assert format_metric_value(5900000.0, "USD") == "$5,900,000.00"


def test_format_usd_value_includes_two_decimal_places():
    assert format_metric_value(33.0, "USD") == "$33.00"


def test_format_percent_value_appends_percent_symbol():
    assert format_metric_value(81.2, "%") == "81.2%"


def test_format_percent_strips_trailing_zeros():
    assert format_metric_value(100.0, "%") == "100%"


def test_format_whole_number_uses_commas_no_decimal_point():
    assert format_metric_value(178700.0, "KW") == "178,700"


def test_format_decimal_number_preserves_decimal():
    assert format_metric_value(178.7, "MW") == "178.7"


def test_format_large_decimal_uses_commas():
    assert format_metric_value(1234567.89, "kW") == "1,234,567.89"


def test_format_nan_returns_empty_string():
    assert format_metric_value(float("nan"), "USD") == ""


def test_format_empty_string_returns_empty_string():
    assert format_metric_value("", "USD") == ""


def test_format_unknown_unit_comma_formats_number():
    assert format_metric_value(33.02, "USD/KW") == "33.02"
