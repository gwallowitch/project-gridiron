import polars as pl
import pytest

from gridiron.validation.turnover_features import validate_turnover_features


def test_missing_schema_fails() -> None:
    with pytest.raises(ValueError, match="missing columns"):
        validate_turnover_features(pl.DataFrame({"game_id": ["g1"]}))
