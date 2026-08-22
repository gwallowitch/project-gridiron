"""Historical NFL game-environment features for Step 82A.

This foundation consumes environment fields already present on the schedule
artifact. It does not fetch live forecasts and makes no predictive-value claim.
"""

from __future__ import annotations

from collections.abc import Iterable

import polars as pl

_REQUIRED = {"game_id", "season", "week", "home_team", "away_team"}

TEMP_COLUMNS = ("temp", "temperature", "game_temp", "weather_temp")
WIND_COLUMNS = ("wind", "wind_speed", "windspeed", "game_wind")
WEATHER_COLUMNS = ("weather", "weather_detail", "conditions", "condition")
ROOF_COLUMNS = ("roof", "roof_type", "stadium_type")
SURFACE_COLUMNS = ("surface", "field_surface")
STADIUM_COLUMNS = ("stadium", "stadium_name", "venue")


def _require(frame: pl.DataFrame) -> None:
    missing = _REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(
            "Schedule is missing required columns: "
            + ", ".join(sorted(missing))
        )


def _first_existing(columns: Iterable[str], frame: pl.DataFrame) -> str | None:
    return next((name for name in columns if name in frame.columns), None)


def _numeric_expr(name: str | None) -> pl.Expr:
    if name is None:
        return pl.lit(None, dtype=pl.Float64)

    # Cast numeric values directly; otherwise extract the first signed decimal
    # from text such as "15 mph" or "72F".
    raw = pl.col(name)
    as_float = raw.cast(pl.Float64, strict=False)
    extracted = (
        raw.cast(pl.String, strict=False)
        .str.extract(r"(-?\d+(?:\.\d+)?)", group_index=1)
        .cast(pl.Float64, strict=False)
    )
    return pl.coalesce(as_float, extracted)


def _text_expr(name: str | None) -> pl.Expr:
    if name is None:
        return pl.lit(None, dtype=pl.String)
    return pl.col(name).cast(pl.String, strict=False)


def build_game_environment_features(schedule: pl.DataFrame) -> pl.DataFrame:
    """Build one environment row per scheduled game."""
    _require(schedule)

    temp_col = _first_existing(TEMP_COLUMNS, schedule)
    wind_col = _first_existing(WIND_COLUMNS, schedule)
    weather_col = _first_existing(WEATHER_COLUMNS, schedule)
    roof_col = _first_existing(ROOF_COLUMNS, schedule)
    surface_col = _first_existing(SURFACE_COLUMNS, schedule)
    stadium_col = _first_existing(STADIUM_COLUMNS, schedule)

    base = schedule.select(
        "game_id",
        "season",
        "week",
        "home_team",
        "away_team",
        _numeric_expr(temp_col).alias("temperature_f"),
        _numeric_expr(wind_col).alias("wind_mph"),
        _text_expr(weather_col).alias("weather_text"),
        _text_expr(roof_col).alias("roof_text"),
        _text_expr(surface_col).alias("surface_text"),
        _text_expr(stadium_col).alias("stadium_text"),
    )

    weather_lower = (
        pl.col("weather_text")
        .fill_null("")
        .str.to_lowercase()
    )
    roof_lower = (
        pl.col("roof_text")
        .fill_null("")
        .str.to_lowercase()
    )

    return (
        base.with_columns(
            roof_lower.str.contains(
                r"dome|indoors?|closed",
            ).alias("indoor_or_closed_roof"),
            roof_lower.str.contains(
                r"retract",
            ).alias("retractable_roof"),
            weather_lower.str.contains(
                r"rain|shower|drizzle|storm",
            ).alias("rain_or_precipitation"),
            weather_lower.str.contains(
                r"snow|flurr|sleet|blizzard",
            ).alias("snow_or_wintry"),
            (pl.col("temperature_f") <= 32.0).alias("extreme_cold"),
            (pl.col("temperature_f") >= 85.0).alias("extreme_heat"),
            (pl.col("wind_mph") >= 15.0).alias("high_wind"),
        )
        .with_columns(
            (
                pl.col("temperature_f").is_not_null()
                | pl.col("wind_mph").is_not_null()
                | pl.col("weather_text").is_not_null()
                | pl.col("roof_text").is_not_null()
            ).alias("environment_known"),
            (
                pl.col("extreme_cold").cast(pl.Int8, strict=False).fill_null(0)
                + pl.col("extreme_heat").cast(pl.Int8, strict=False).fill_null(0)
                + pl.col("high_wind").cast(pl.Int8, strict=False).fill_null(0)
                + pl.col("rain_or_precipitation").cast(pl.Int8, strict=False)
                + pl.col("snow_or_wintry").cast(pl.Int8, strict=False)
            ).alias("adverse_weather_count"),
        )
        .with_columns(
            (
                pl.col("adverse_weather_count") > 0
            ).alias("adverse_weather")
        )
    )
