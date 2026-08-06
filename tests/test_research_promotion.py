from __future__ import annotations

from gridiron.research.promotion import PromotionStatus, review_candidate
from gridiron.research.statistics import CandidateStatistics


def stats(
    mean_delta: float,
    interval_high: float,
    accuracy_delta: float = 0.0,
) -> CandidateStatistics:
    return CandidateStatistics(
        name="candidate",
        seasons=4,
        wins=4,
        losses=0,
        ties=0,
        mean_score_delta=mean_delta,
        median_score_delta=mean_delta,
        score_delta_stddev=0.001,
        confidence_interval_low=-0.003,
        confidence_interval_high=interval_high,
        mean_accuracy_delta=accuracy_delta,
        mean_brier_delta=-0.001,
        mean_log_loss_delta=-0.001,
        mean_margin_mae_delta=-0.01,
        mean_margin_rmse_delta=-0.01,
    )


def test_pass() -> None:
    assert review_candidate(
        stats(-0.002, -0.0002)
    ).status == PromotionStatus.PASS


def test_inconclusive() -> None:
    assert review_candidate(
        stats(-0.002, 0.0001)
    ).status == PromotionStatus.INCONCLUSIVE


def test_reject() -> None:
    assert review_candidate(
        stats(0.001, 0.002)
    ).status == PromotionStatus.REJECT


def test_accuracy_floor() -> None:
    assert review_candidate(
        stats(-0.002, -0.0002, -0.01)
    ).status == PromotionStatus.REJECT
