from __future__ import annotations

from gridiron.experiments.models import ExperimentConfig, ExperimentResult
from gridiron.research.decision import build_promotion_decision
from gridiron.research.models import ResearchRun, SeasonResearchResult
from gridiron.research.promotion import PromotionStatus


def result(name:str,season:int,score:float,accuracy:float)->ExperimentResult:
    return ExperimentResult.create(config=ExperimentConfig(name=name,home_field_advantage=1.5,probability_scale=0.14,margin_scale=0.75,rest_weight=0.0),season=season,games_evaluated=100,winner_accuracy=accuracy,brier_score=0.23,log_loss=0.66,margin_mae=10.5,margin_rmse=13.3,selection_score=score)
def run(candidate_delta:float)->ResearchRun:
    seasons=(2022,2023,2024,2025)
    return ResearchRun(profile='modern',seasons=seasons,experiment_count=2,total_runs=8,runtime_seconds=1.0,generated_at='now',git_commit='abc123',python_version='3.13',results=tuple(SeasonResearchResult(season=s,experiments=(result('rest_020',s,0.47+candidate_delta,0.615),result('rest_000_baseline',s,0.47,0.607))) for s in seasons))
def test_pass_candidate_is_recommended()->None:
    d=build_promotion_decision(run(-0.002)); assert d.recommendation==PromotionStatus.PASS; assert d.recommended_candidate=='rest_020'; assert d.approval_required is True
def test_nonpassing_candidate_is_not_recommended()->None:
    d=build_promotion_decision(run(0.001)); assert d.recommendation==PromotionStatus.REJECT; assert d.recommended_candidate is None; assert d.approval_required is False
