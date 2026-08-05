from __future__ import annotations

import pytest

from gridiron.research.validation import validate_profiles


def test_empty_profiles_are_rejected() -> None:
    with pytest.raises(ValueError, match="at least one profile"):
        validate_profiles({}, (2020,))


def test_invalid_seasons_are_rejected() -> None:
    with pytest.raises(ValueError, match="invalid seasons"):
        validate_profiles({"bad": (1800,)}, (2020,))


def test_duplicate_exclusions_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicates"):
        validate_profiles({"modern": (2022,)}, (2020, 2020))
