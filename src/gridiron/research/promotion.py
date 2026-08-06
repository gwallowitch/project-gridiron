"""Evidence-based promotion review for research candidates."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from gridiron.research.statistics import CandidateStatistics


class PromotionStatus(StrEnum):
    """Available research promotion outcomes."""

    PASS = "PASS"
    INCONCLUSIVE = "INCONCLUSIVE"
    REJECT = "REJECT"


@dataclass(frozen=True, slots=True)
class PromotionReview:
    """Promotion decision and supporting explanation."""

    candidate: str
    status: PromotionStatus
    reason: str


def review_candidate(
    statistics: CandidateStatistics,
    *,
    practical_score_threshold: float = 0.001,
    accuracy_floor: float = -0.002,
    minimum_seasons: int = 4,
) -> PromotionReview:
    """Classify a candidate using paired multi-season evidence."""
    improvement = -statistics.mean_score_delta

    if statistics.mean_score_delta >= 0.0:
        return PromotionReview(
            statistics.name,
            PromotionStatus.REJECT,
            "Average selection score did not improve versus baseline.",
        )

    if statistics.mean_accuracy_delta < accuracy_floor:
        return PromotionReview(
            statistics.name,
            PromotionStatus.REJECT,
            "Winner accuracy degradation exceeded the allowed floor.",
        )

    checks = (
        statistics.seasons >= minimum_seasons,
        statistics.confidence_interval_high < 0.0,
        improvement >= practical_score_threshold,
        statistics.wins > statistics.losses,
    )
    if all(checks):
        return PromotionReview(
            statistics.name,
            PromotionStatus.PASS,
            (
                "Improvement is practical, the confidence interval excludes "
                "zero, and season wins exceed losses."
            ),
        )

    reasons = []
    if not checks[0]:
        reasons.append("too few seasons")
    if not checks[1]:
        reasons.append("confidence interval includes zero")
    if not checks[2]:
        reasons.append("improvement is below the practical threshold")
    if not checks[3]:
        reasons.append("season wins do not exceed losses")

    return PromotionReview(
        statistics.name,
        PromotionStatus.INCONCLUSIVE,
        "; ".join(reasons).capitalize() + ".",
    )
