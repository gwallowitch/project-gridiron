"""Research-profile configuration loading."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from gridiron.research.validation import validate_profiles


@dataclass(frozen=True, slots=True)
class ResearchProfiles:
    """Named season collections for multi-season research."""

    profiles: dict[str, tuple[int, ...]]
    excluded_seasons: tuple[int, ...]

    def seasons_for(self, name: str) -> tuple[int, ...]:
        """Return seasons for a named profile."""
        try:
            return self.profiles[name]
        except KeyError as exc:
            choices = ", ".join(sorted(self.profiles))
            raise KeyError(
                f"Unknown research profile {name!r}. "
                f"Available profiles: {choices}"
            ) from exc


def load_research_profiles(path: Path) -> ResearchProfiles:
    """Load and validate named research profiles from TOML."""
    if not path.exists():
        raise FileNotFoundError(
            f"Research configuration does not exist: {path}"
        )

    with path.open("rb") as handle:
        payload = tomllib.load(handle)

    raw_profiles = payload.get("profiles", {})
    raw_excluded = payload.get("exclude", {}).get("seasons", [])

    profiles = {
        str(name): tuple(int(season) for season in seasons)
        for name, seasons in raw_profiles.items()
    }
    excluded = tuple(int(season) for season in raw_excluded)

    validate_profiles(profiles, excluded)
    return ResearchProfiles(
        profiles=profiles,
        excluded_seasons=excluded,
    )
