"""
Demo context values for the readiness workbook builder.

Provides deterministic demo client metadata for generating reproducible demo
outputs from the canonical blank intake template (examples/readiness_demo/).
"""

from __future__ import annotations

from datetime import date
from typing import Any

DEMO_CONTEXT_DATE = date(2025, 1, 1)

DEMO_CLIENT_VALUES: dict[str, Any] = {
    "client_name": "Demo AI Infrastructure Co.",
    "project_name": "Midwest AI Campus Requirement",
    "project_id": "DEMO-READY-001",
    "project_type": "AI training campus",
    "buyer_profile": "Occupier",
    "target_market": "Midwest",
    "target_region": "Missouri / Central US",
    "target_capacity_mw": 250,
    "target_rack_density_kw": 50,
    "target_live_date": date(2027, 12, 31),
    "readiness_stage": "Pre-RFP / requirement definition",
    "primary_use_case": "Large-scale AI training and inference",
    "prepared_for": "Internal investment committee",
    "prepared_by": "Financial Data Analytics prototype",
    "prepared_date": DEMO_CONTEXT_DATE,
    "version": "v0.1 demo",
    "confidentiality": "Demo only",
    "executive_summary": (
        "Demo project used to evaluate whether a data center requirement "
        "is ready to transact."
    ),
    "key_decision_question": (
        "Is this project sufficiently defined to enter an RFP or "
        "broker-led market process?"
    ),
    # Map to existing intake-linked fields so PowerBI_Export reflects demo state.
    "assessment_date": DEMO_CONTEXT_DATE,
    "use_case": "Large-scale AI training and inference",
    "project_stage": "Pre-RFP / requirement definition",
    "preferred_markets": "Midwest",
    "initial_critical_it_mw": 250,
}


def apply_demo_context(client: dict) -> dict:
    """Return a new client dict with demo metadata merged over the source client values.

    All keys from the source client are preserved so Requirement_Map intake_field
    references continue to resolve. Demo values take precedence for fields they define.
    """
    merged = dict(client)
    merged.update(DEMO_CLIENT_VALUES)
    return merged
