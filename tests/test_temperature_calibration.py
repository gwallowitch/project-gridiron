import math

import polars as pl
import pytest

from gridiron.calibration.temperature import (
    TemperatureCalibrationContract,
    apply_temperature_calibration,
    calibrate_probability,
)


def test_half_probability_is_fixed_point() -> None:
    assert calibrate_probability(
        0.5,
        slope=0.8,
    ) == 0.5


def test_temperature_preserves_winner_side() -> None:
    for probability in (
        0.01,
        0.10,
        0.25,
        0.49,
        0.51,
        0.75,
        0.90,
        0.99,
    ):
        calibrated = calibrate_probability(
            probability,
            slope=0.8,
        )
        assert (
            probability >= 0.5
        ) == (
            calibrated >= 0.5
        )


def test_temperature_is_monotonic() -> None:
    raw = [
        0.1,
        0.2,
        0.4,
        0.5,
        0.6,
        0.8,
        0.9,
    ]
    calibrated = [
        calibrate_probability(
            value,
            slope=0.8,
        )
        for value in raw
    ]

    assert calibrated == sorted(calibrated)


def test_extremes_remain_exact() -> None:
    assert calibrate_probability(
        0.0,
        slope=0.8,
    ) == 0.0
    assert calibrate_probability(
        1.0,
        slope=0.8,
    ) == 1.0


def test_invalid_probability_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="between 0.0 and 1.0",
    ):
        calibrate_probability(
            1.1,
            slope=0.8,
        )


def test_invalid_slope_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="slope",
    ):
        calibrate_probability(
            0.7,
            slope=0.0,
        )


def test_frame_application_creates_output() -> None:
    frame = pl.DataFrame(
        {
            "p": [
                0.25,
                0.50,
                0.75,
            ]
        }
    )

    out = apply_temperature_calibration(
        frame,
        probability_column="p",
        output_column="p_cal",
        slope=0.8,
    )

    assert "p_cal" in out.columns
    assert out["p_cal"][1] == 0.5


def test_contract_validation() -> None:
    contract = TemperatureCalibrationContract(
        method="temperature",
        slope=0.8,
        intercept=0.0,
        source_step="88D",
        source_fingerprint_sha256="a" * 64,
        training_seasons=(
            2022,
            2023,
            2024,
            2025,
        ),
        population_games=1138,
    )

    contract.validate()


def test_calibration_output_is_finite() -> None:
    value = calibrate_probability(
        0.999999,
        slope=0.8,
    )

    assert math.isfinite(value)
    assert 0.0 < value < 1.0
