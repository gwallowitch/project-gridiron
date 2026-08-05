"""Validation for research profiles and runs."""

from __future__ import annotations


def validate_profiles(
    profiles: dict[str, tuple[int, ...]],
    excluded_seasons: tuple[int, ...],
) -> None:
    """Raise when research-profile configuration is invalid."""
    if not profiles:
        raise ValueError(
            "Research configuration must define at least one profile."
        )

    excluded = set(excluded_seasons)
    if len(excluded) != len(excluded_seasons):
        raise ValueError("Excluded seasons contain duplicates.")

    for name, seasons in profiles.items():
        if not name.strip():
            raise ValueError("Research profile names cannot be blank.")
        if not seasons:
            raise ValueError(
                f"Research profile {name!r} contains no seasons."
            )
        if len(set(seasons)) != len(seasons):
            raise ValueError(
                f"Research profile {name!r} contains duplicate seasons."
            )
        invalid = [
            season
            for season in seasons
            if season < 1999 or season > 2100
        ]
        if invalid:
            raise ValueError(
                f"Research profile {name!r} contains invalid seasons: "
                f"{invalid}"
            )
        overlap = sorted(set(seasons).intersection(excluded))
        if overlap:
            raise ValueError(
                f"Research profile {name!r} includes excluded seasons: "
                f"{overlap}"
            )
