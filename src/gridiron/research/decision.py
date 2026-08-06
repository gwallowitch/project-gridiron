"""Promotion decision ranking for Project Gridiron research."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from gridiron.research.models import ResearchRun
from gridiron.research.promotion import (
    PromotionReview,
    PromotionStatus,
    review_candidate,
)
from gridiron.research.statistics import CandidateStatistics, analyze_candidates

_STATUS_RANK={PromotionStatus.PASS:0,PromotionStatus.INCONCLUSIVE:1,PromotionStatus.REJECT:2}
@dataclass(frozen=True, slots=True)
class PromotionCandidate:
    rank:int; name:str; status:PromotionStatus; reason:str; seasons:int; wins:int; losses:int; ties:int; mean_score_delta:float; confidence_interval_low:float; confidence_interval_high:float; mean_accuracy_delta:float
    def to_dict(self)->dict[str,Any]:
        payload=asdict(self); payload['status']=self.status.value; return payload
@dataclass(frozen=True, slots=True)
class PromotionDecision:
    profile:str; baseline:str; recommended_candidate:str|None; recommendation:PromotionStatus; approval_required:bool; reason:str; generated_at:str; git_commit:str|None; candidates:tuple[PromotionCandidate,...]
    def to_dict(self)->dict[str,Any]:
        return {'profile':self.profile,'baseline':self.baseline,'recommended_candidate':self.recommended_candidate,'recommendation':self.recommendation.value,'approval_required':self.approval_required,'reason':self.reason,'generated_at':self.generated_at,'git_commit':self.git_commit,'candidates':[c.to_dict() for c in self.candidates]}
def build_promotion_decision(run:ResearchRun,*,baseline_name:str='rest_000_baseline')->PromotionDecision:
    statistics=analyze_candidates(run,baseline_name=baseline_name)
    if not statistics: raise ValueError('Promotion decision requires at least one candidate.')
    reviewed=[(item,review_candidate(item)) for item in statistics]
    reviewed.sort(key=_decision_sort_key)
    candidates=tuple(_candidate_from_review(rank,item,review) for rank,(item,review) in enumerate(reviewed,start=1))
    leader=candidates[0]
    recommended=leader.name if leader.status==PromotionStatus.PASS else None
    reason=leader.reason if recommended is not None else f'No candidate currently satisfies every promotion rule. Strongest candidate: {leader.name}. {leader.reason}'
    return PromotionDecision(profile=run.profile,baseline=baseline_name,recommended_candidate=recommended,recommendation=leader.status,approval_required=recommended is not None,reason=reason,generated_at=datetime.now(UTC).isoformat(),git_commit=run.git_commit,candidates=candidates)
def _decision_sort_key(item:tuple[CandidateStatistics,PromotionReview])->tuple[int,float,float,str]:
    statistics,review=item
    return (_STATUS_RANK[review.status],statistics.mean_score_delta,-statistics.mean_accuracy_delta,statistics.name)
def _candidate_from_review(rank:int,statistics:CandidateStatistics,review:PromotionReview)->PromotionCandidate:
    return PromotionCandidate(rank=rank,name=statistics.name,status=review.status,reason=review.reason,seasons=statistics.seasons,wins=statistics.wins,losses=statistics.losses,ties=statistics.ties,mean_score_delta=statistics.mean_score_delta,confidence_interval_low=statistics.confidence_interval_low,confidence_interval_high=statistics.confidence_interval_high,mean_accuracy_delta=statistics.mean_accuracy_delta)
