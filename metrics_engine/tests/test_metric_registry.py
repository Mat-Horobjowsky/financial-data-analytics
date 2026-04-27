import pytest
import yaml
from metrics_engine.metric_registry import load_metric_registry, MetricRegistryError


def _write(tmp_path, content: dict):
    path = tmp_path / "metrics.yaml"
    path.write_text(yaml.dump(content))
    return path


def _sum_metric(id="rev", **overrides):
    m = {
        "id": id,
        "label": "Revenue",
        "type": "sum",
        "unit": "USD",
        "decimals": 0,
        "description": "Total revenue",
        "source_col": "revenue",
    }
    m.update(overrides)
    return m


def _valid_yaml(metrics=None, rollups=None):
    return {
        "segment_rollups": rollups if rollups is not None else [["region"]],
        "metrics": metrics if metrics is not None else [_sum_metric()],
    }


# ── happy path ────────────────────────────────────────────────────────────────

def test_returns_metrics_keyed_by_id(tmp_path):
    path = _write(tmp_path, _valid_yaml())
    registry = load_metric_registry(path)
    assert "rev" in registry["metrics"]


def test_returns_segment_rollups(tmp_path):
    path = _write(tmp_path, _valid_yaml(rollups=[["region"], ["region", "provider"]]))
    registry = load_metric_registry(path)
    assert registry["segment_rollups"] == [["region"], ["region", "provider"]]


def test_sum_metric_fields_preserved(tmp_path):
    path = _write(tmp_path, _valid_yaml())
    m = load_metric_registry(path)["metrics"]["rev"]
    assert m["label"] == "Revenue"
    assert m["type"] == "sum"
    assert m["unit"] == "USD"
    assert m["decimals"] == 0
    assert m["source_col"] == "revenue"


def test_loads_ratio_metric(tmp_path):
    m = {
        "id": "util",
        "label": "Utilization",
        "type": "ratio",
        "unit": "%",
        "decimals": 1,
        "description": "leased/capacity",
        "numerator": "leased_mw",
        "denominator": "capacity_mw",
        "scale": 100,
    }
    path = _write(tmp_path, _valid_yaml(metrics=[m]))
    registry = load_metric_registry(path)
    assert "util" in registry["metrics"]


def test_loads_per_unit_metric(tmp_path):
    m = {
        "id": "rev_mw",
        "label": "Revenue per MW",
        "type": "per_unit",
        "unit": "USD/MW",
        "decimals": 2,
        "description": "revenue per leased mw",
        "numerator": "revenue",
        "denominator": "leased_mw",
    }
    path = _write(tmp_path, _valid_yaml(metrics=[m]))
    registry = load_metric_registry(path)
    assert "rev_mw" in registry["metrics"]


def test_accepts_empty_segment_rollups(tmp_path):
    path = _write(tmp_path, _valid_yaml(rollups=[]))
    registry = load_metric_registry(path)
    assert registry["segment_rollups"] == []


def test_accepts_multiple_metrics(tmp_path):
    metrics = [_sum_metric("a"), _sum_metric("b", source_col="capacity_mw")]
    path = _write(tmp_path, _valid_yaml(metrics=metrics))
    registry = load_metric_registry(path)
    assert set(registry["metrics"].keys()) == {"a", "b"}


# ── segment_rollups validation ────────────────────────────────────────────────

def test_rejects_missing_segment_rollups(tmp_path):
    data = _valid_yaml()
    del data["segment_rollups"]
    path = _write(tmp_path, data)
    with pytest.raises(MetricRegistryError, match="segment_rollups"):
        load_metric_registry(path)


def test_rejects_segment_rollups_not_a_list(tmp_path):
    path = _write(tmp_path, _valid_yaml(rollups="region"))
    with pytest.raises(MetricRegistryError, match="segment_rollups"):
        load_metric_registry(path)


def test_rejects_segment_rollup_item_that_is_a_string(tmp_path):
    path = _write(tmp_path, _valid_yaml(rollups=["region"]))
    with pytest.raises(MetricRegistryError, match="segment_rollups"):
        load_metric_registry(path)


def test_rejects_segment_rollup_item_that_is_not_all_strings(tmp_path):
    path = _write(tmp_path, _valid_yaml(rollups=[[1, "region"]]))
    with pytest.raises(MetricRegistryError, match="segment_rollups"):
        load_metric_registry(path)


# ── metrics list validation ───────────────────────────────────────────────────

def test_rejects_missing_metrics_key(tmp_path):
    data = _valid_yaml()
    del data["metrics"]
    path = _write(tmp_path, data)
    with pytest.raises(MetricRegistryError, match="metrics"):
        load_metric_registry(path)


def test_rejects_empty_metrics_list(tmp_path):
    path = _write(tmp_path, _valid_yaml(metrics=[]))
    with pytest.raises(MetricRegistryError, match="metrics"):
        load_metric_registry(path)


def test_rejects_duplicate_metric_ids(tmp_path):
    path = _write(tmp_path, _valid_yaml(metrics=[_sum_metric("x"), _sum_metric("x")]))
    with pytest.raises(MetricRegistryError, match="[Dd]uplicate"):
        load_metric_registry(path)


def test_rejects_unknown_metric_type(tmp_path):
    path = _write(tmp_path, _valid_yaml(metrics=[_sum_metric(type="average")]))
    with pytest.raises(MetricRegistryError, match="[Tt]ype"):
        load_metric_registry(path)


# ── required common fields ────────────────────────────────────────────────────

@pytest.mark.parametrize("field", ["id", "label", "type", "unit", "decimals", "description"])
def test_rejects_missing_required_field(tmp_path, field):
    m = _sum_metric()
    del m[field]
    path = _write(tmp_path, _valid_yaml(metrics=[m]))
    with pytest.raises(MetricRegistryError, match=field):
        load_metric_registry(path)


# ── sum-type field rules ──────────────────────────────────────────────────────

def test_sum_rejects_missing_source_col(tmp_path):
    m = _sum_metric()
    del m["source_col"]
    path = _write(tmp_path, _valid_yaml(metrics=[m]))
    with pytest.raises(MetricRegistryError, match="source_col"):
        load_metric_registry(path)


def test_sum_rejects_numerator(tmp_path):
    path = _write(tmp_path, _valid_yaml(metrics=[_sum_metric(numerator="x")]))
    with pytest.raises(MetricRegistryError, match="numerator"):
        load_metric_registry(path)


def test_sum_rejects_denominator(tmp_path):
    path = _write(tmp_path, _valid_yaml(metrics=[_sum_metric(denominator="x")]))
    with pytest.raises(MetricRegistryError, match="denominator"):
        load_metric_registry(path)


# ── ratio-type field rules ────────────────────────────────────────────────────

def _ratio_metric(**overrides):
    m = {
        "id": "r",
        "label": "Ratio",
        "type": "ratio",
        "unit": "%",
        "decimals": 1,
        "description": "a ratio",
        "numerator": "leased_mw",
        "denominator": "capacity_mw",
        "scale": 100,
    }
    m.update(overrides)
    return m


def test_ratio_rejects_missing_numerator(tmp_path):
    m = _ratio_metric()
    del m["numerator"]
    path = _write(tmp_path, _valid_yaml(metrics=[m]))
    with pytest.raises(MetricRegistryError, match="numerator"):
        load_metric_registry(path)


def test_ratio_rejects_missing_denominator(tmp_path):
    m = _ratio_metric()
    del m["denominator"]
    path = _write(tmp_path, _valid_yaml(metrics=[m]))
    with pytest.raises(MetricRegistryError, match="denominator"):
        load_metric_registry(path)


def test_ratio_rejects_missing_scale(tmp_path):
    m = _ratio_metric()
    del m["scale"]
    path = _write(tmp_path, _valid_yaml(metrics=[m]))
    with pytest.raises(MetricRegistryError, match="scale"):
        load_metric_registry(path)


def test_ratio_rejects_source_col(tmp_path):
    path = _write(tmp_path, _valid_yaml(metrics=[_ratio_metric(source_col="x")]))
    with pytest.raises(MetricRegistryError, match="source_col"):
        load_metric_registry(path)


# ── per_unit-type field rules ─────────────────────────────────────────────────

def _per_unit_metric(**overrides):
    m = {
        "id": "pu",
        "label": "Per Unit",
        "type": "per_unit",
        "unit": "USD/MW",
        "decimals": 2,
        "description": "per unit",
        "numerator": "revenue",
        "denominator": "leased_mw",
    }
    m.update(overrides)
    return m


def test_per_unit_rejects_missing_numerator(tmp_path):
    m = _per_unit_metric()
    del m["numerator"]
    path = _write(tmp_path, _valid_yaml(metrics=[m]))
    with pytest.raises(MetricRegistryError, match="numerator"):
        load_metric_registry(path)


def test_per_unit_rejects_missing_denominator(tmp_path):
    m = _per_unit_metric()
    del m["denominator"]
    path = _write(tmp_path, _valid_yaml(metrics=[m]))
    with pytest.raises(MetricRegistryError, match="denominator"):
        load_metric_registry(path)


def test_per_unit_rejects_source_col(tmp_path):
    path = _write(tmp_path, _valid_yaml(metrics=[_per_unit_metric(source_col="x")]))
    with pytest.raises(MetricRegistryError, match="source_col"):
        load_metric_registry(path)
