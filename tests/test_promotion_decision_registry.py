from __future__ import annotations

import json
from pathlib import Path

from gridiron.research.decision import PromotionDecision
from gridiron.research.decision_registry import (
    append_promotion_history,
    write_promotion_decision,
)
from gridiron.research.promotion import PromotionStatus


def decision()->PromotionDecision:
    return PromotionDecision(profile='modern',baseline='rest_000_baseline',recommended_candidate=None,recommendation=PromotionStatus.INCONCLUSIVE,approval_required=False,reason='More evidence is required.',generated_at='now',git_commit='abc123',candidates=())
def test_writes_current_decision(tmp_path:Path)->None:
    path=tmp_path/'promotion_decision.json'; write_promotion_decision(path,decision()); payload=json.loads(path.read_text(encoding='utf-8')); assert payload['recommendation']=='INCONCLUSIVE'
def test_appends_history(tmp_path:Path)->None:
    path=tmp_path/'promotion_history.json'; append_promotion_history(path,decision()); append_promotion_history(path,decision()); payload=json.loads(path.read_text(encoding='utf-8')); assert len(payload)==2
