from __future__ import annotations

from pathlib import Path

import pytest

from gridiron.experiments.config import load_experiments


def test_load_experiments_reads_optional_defaults(tmp_path: Path) -> None:
    path = tmp_path / "experiments.toml"
    path.write_text(
        '[[experiment]]\nname="baseline"\n'
        'home_field_advantage=1.5\nprobability_scale=0.18\n'
    )

    result = load_experiments(path)

    assert len(result) == 1
    assert result[0].margin_scale == 1.0
    assert result[0].margin_intercept == 0.0


def test_load_experiments_rejects_duplicate_names(tmp_path: Path) -> None:
    path = tmp_path / "experiments.toml"
    path.write_text(
        '[[experiment]]\nname="same"\n'
        'home_field_advantage=1.5\nprobability_scale=0.18\n'
        '[[experiment]]\nname="same"\n'
        'home_field_advantage=2.0\nprobability_scale=0.16\n'
    )

    with pytest.raises(ValueError, match="names must be unique"):
        load_experiments(path)
