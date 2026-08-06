from __future__ import annotations

from gridiron.research.decision import PromotionDecision
from gridiron.research.decision_report import format_promotion_decision
from gridiron.research.promotion import PromotionStatus


def test_report_shows_approval_gate()->None:
    d=PromotionDecision(profile='modern',baseline='rest_000_baseline',recommended_candidate=None,recommendation=PromotionStatus.INCONCLUSIVE,approval_required=False,reason='More evidence is required.',generated_at='now',git_commit=None,candidates=())
    report=format_promotion_decision(d); assert 'PROJECT GRIDIRON PROMOTION DECISION' in report; assert 'Human approval required... NO' in report
