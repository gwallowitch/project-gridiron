from __future__ import annotations

from pathlib import Path

import pytest

from gridiron.research.config import load_research_profiles


def write_config(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "research.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_loads_named_profiles(tmp_path: Path) -> None:
    path = write_config(
        tmp_path,
        """
[profiles]
modern = [2022, 2023, 2024, 2025]
transition = [2021]

[exclude]
seasons = [2020]
""",
    )

    profiles = load_research_profiles(path)

    assert profiles.seasons_for("modern") == (
        2022,
        2023,
        2024,
        2025,
    )
    assert profiles.excluded_seasons == (2020,)


def test_unknown_profile_has_clear_error(tmp_path: Path) -> None:
    path = write_config(
        tmp_path,
        """
[profiles]
modern = [2022]

[exclude]
seasons = [2020]
""",
    )
    profiles = load_research_profiles(path)

    with pytest.raises(KeyError, match="Available profiles"):
        profiles.seasons_for("missing")


def test_excluded_season_cannot_appear_in_profile(
    tmp_path: Path,
) -> None:
    path = write_config(
        tmp_path,
        """
[profiles]
modern = [2020, 2022]

[exclude]
seasons = [2020]
""",
    )

    with pytest.raises(ValueError, match="excluded seasons"):
        load_research_profiles(path)


def test_duplicate_profile_seasons_are_rejected(
    tmp_path: Path,
) -> None:
    path = write_config(
        tmp_path,
        """
[profiles]
modern = [2022, 2022]

[exclude]
seasons = [2020]
""",
    )

    with pytest.raises(ValueError, match="duplicate"):
        load_research_profiles(path)
