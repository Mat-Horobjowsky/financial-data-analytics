from pathlib import Path

import yaml


class MetricRegistryError(Exception):
    pass


_SUPPORTED_TYPES = {"sum", "ratio", "per_unit", "count", "conditional_count", "completion_pct"}
_COMMON_REQUIRED = ("id", "label", "type", "unit", "decimals", "description")

_TYPE_REQUIRED = {
    "sum": ("source_col",),
    "ratio": ("numerator", "denominator", "scale"),
    "per_unit": ("numerator", "denominator"),
    "count": (),
    "conditional_count": ("source_col", "condition_values"),
    "completion_pct": ("source_col", "complete_values", "scale"),
}
_TYPE_FORBIDDEN = {
    "sum": ("numerator", "denominator"),
    "ratio": ("source_col",),
    "per_unit": ("source_col",),
    "count": ("source_col", "numerator", "denominator", "condition_values", "complete_values"),
    "conditional_count": ("numerator", "denominator", "complete_values"),
    "completion_pct": ("numerator", "denominator", "condition_values"),
}


def _validate_segment_rollups(rollups) -> list[list[str]]:
    if not isinstance(rollups, list):
        raise MetricRegistryError(
            f"segment_rollups must be a list of lists, got {type(rollups).__name__}"
        )
    for i, item in enumerate(rollups):
        if not isinstance(item, list):
            raise MetricRegistryError(
                f"segment_rollups[{i}] must be a list of column names, got {type(item).__name__}: {item!r}"
            )
        for col in item:
            if not isinstance(col, str):
                raise MetricRegistryError(
                    f"segment_rollups[{i}] must contain only strings, got {type(col).__name__}: {col!r}"
                )
    return rollups


def _validate_metric(m: dict, index: int) -> dict:
    for field in _COMMON_REQUIRED:
        if field not in m:
            raise MetricRegistryError(
                f"metrics[{index}] missing required field '{field}'"
            )

    metric_type = m["type"]
    if metric_type not in _SUPPORTED_TYPES:
        raise MetricRegistryError(
            f"metrics[{index}] (id={m.get('id')!r}): unsupported type {metric_type!r}. "
            f"Allowed: {sorted(_SUPPORTED_TYPES)}"
        )

    for field in _TYPE_REQUIRED[metric_type]:
        if field not in m:
            raise MetricRegistryError(
                f"metrics[{index}] (id={m['id']!r}, type={metric_type!r}): "
                f"missing required field '{field}'"
            )

    for field in _TYPE_FORBIDDEN[metric_type]:
        if field in m:
            raise MetricRegistryError(
                f"metrics[{index}] (id={m['id']!r}, type={metric_type!r}): "
                f"field '{field}' is not allowed for type '{metric_type}'"
            )

    for list_field in ("condition_values", "complete_values"):
        if list_field in m:
            if not isinstance(m[list_field], list):
                raise MetricRegistryError(
                    f"metrics[{index}] (id={m['id']!r}): '{list_field}' must be a list"
                )
            if not m[list_field]:
                raise MetricRegistryError(
                    f"metrics[{index}] (id={m['id']!r}): '{list_field}' must not be empty"
                )

    return m


def load_metric_registry(path: str | Path) -> dict:
    with open(path) as f:
        data = yaml.safe_load(f)

    if "segment_rollups" not in data:
        raise MetricRegistryError("Config missing required key 'segment_rollups'")
    segment_rollups = _validate_segment_rollups(data["segment_rollups"])

    if "metrics" not in data:
        raise MetricRegistryError("Config missing required key 'metrics'")
    raw_metrics = data["metrics"]
    if not raw_metrics:
        raise MetricRegistryError("'metrics' must be a non-empty list")

    seen_ids: set[str] = set()
    metrics: dict[str, dict] = {}
    for i, m in enumerate(raw_metrics):
        _validate_metric(m, i)
        mid = m["id"]
        if mid in seen_ids:
            raise MetricRegistryError(f"Duplicate metric id: {mid!r}")
        seen_ids.add(mid)
        metrics[mid] = m

    return {"metrics": metrics, "segment_rollups": segment_rollups}
