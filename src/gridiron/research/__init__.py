"""Multi-season research public API."""

from gridiron.research.aggregation import (
    ResearchAggregate as ResearchAggregate,
)
from gridiron.research.aggregation import (
    aggregate_research as aggregate_research,
)
from gridiron.research.config import (
    ResearchProfiles as ResearchProfiles,
)
from gridiron.research.config import (
    load_research_profiles as load_research_profiles,
)
from gridiron.research.models import (
    ResearchRun as ResearchRun,
)
from gridiron.research.models import (
    SeasonResearchResult as SeasonResearchResult,
)
from gridiron.research.promotion import (
    PromotionReview as PromotionReview,
)
from gridiron.research.promotion import (
    PromotionStatus as PromotionStatus,
)
from gridiron.research.promotion import (
    review_candidate as review_candidate,
)
from gridiron.research.runner import run_research as run_research
from gridiron.research.statistics import (
    CandidateStatistics as CandidateStatistics,
)
from gridiron.research.statistics import (
    analyze_candidates as analyze_candidates,
)

__all__ = [
    "CandidateStatistics",
    "PromotionReview",
    "PromotionStatus",
    "ResearchAggregate",
    "ResearchProfiles",
    "ResearchRun",
    "SeasonResearchResult",
    "aggregate_research",
    "analyze_candidates",
    "load_research_profiles",
    "review_candidate",
    "run_research",
]
