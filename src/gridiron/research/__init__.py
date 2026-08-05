"""Multi-season research public API."""

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
from gridiron.research.runner import (
    run_research as run_research,
)

__all__ = [
    "ResearchProfiles",
    "ResearchRun",
    "SeasonResearchResult",
    "load_research_profiles",
    "run_research",
]
