"""Non-activating Core-Three normalization and preview orchestration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from gridiron.market.core_three_consensus import build_consensus_preview
from gridiron.market.core_three_provider import normalize_event_response


def preview_non_evidence(
    response: Mapping[str, Any],
    authoritative_event: Mapping[str, Any],
    *,
    receipt_at: str,
    timestamp_semantics_approved_for_test: bool = False,
) -> dict[str, Any]:
    """Return a sanitized preview; no manifest, ledger, raw file, or evidence write."""
    observation = normalize_event_response(
        response,
        authoritative_event,
        receipt_at=receipt_at,
        timestamp_semantics_approved=timestamp_semantics_approved_for_test,
    )
    return {
        "classification": "STEP91O_CORE_THREE_NON_PROSPECTIVE_PREVIEW",
        "warning": "NOT PROSPECTIVE EVIDENCE; COLLECTION IS INACTIVE",
        "observation": observation.as_normalized_dict(),
        "consensus": build_consensus_preview(observation),
        "manifest_touched": False,
        "ledger_touched": False,
        "raw_payload_retained": False,
        "prospective_evidence_count": 0,
        "activation_allowed": False,
    }


__all__ = ["preview_non_evidence"]
