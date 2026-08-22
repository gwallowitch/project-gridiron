"""Configuration-driven prediction experiment runner."""
from __future__ import annotations

import polars as pl

from gridiron.backtest.evaluator import evaluate_predictions
from gridiron.experiments.models import ExperimentConfig, ExperimentResult
from gridiron.experiments.validation import validate_experiments
from gridiron.prediction.confidence import classify_confidence
from gridiron.prediction.engine import build_predictions
from gridiron.prediction.probability import home_win_probability

_REQUIRED_REST_COLUMNS = frozenset({"game_id", "rest_advantage"})
_REQUIRED_QB_COLUMNS = frozenset({"game_id", "qb_rating_difference"})
_REQUIRED_INJURY_COLUMNS = frozenset(
    {"game_id", "injury_score_difference", "source_timestamp_available"}
)
_REQUIRED_EARLY_DOWN_COLUMNS = frozenset(
    {
        "game_id",
        "early_down_off_epa_difference",
        "early_down_def_epa_difference",
        "early_down_success_difference",
        "home_early_down_known",
        "away_early_down_known",
    }
)
_REQUIRED_TURNOVER_COLUMNS = frozenset(
    {
        "game_id",
        "interception_rate_difference",
        "fumble_lost_rate_difference",
        "home_turnover_known",
        "away_turnover_known",
    }
)
_REQUIRED_PASSING_COLUMNS = frozenset(
    {
        "game_id",
        "pass_off_epa_difference",
        "pass_def_epa_difference",
        "pass_success_difference",
        "off_sack_rate_advantage",
        "def_sack_rate_advantage",
        "explosive_pass_rate_difference",
        "home_passing_known",
        "away_passing_known",
    }
)
_REQUIRED_RED_ZONE_COLUMNS = frozenset(
    {
        "game_id",
        "red_zone_off_epa_difference",
        "red_zone_def_epa_difference",
        "red_zone_success_difference",
        "red_zone_td_rate_difference",
        "home_red_zone_known",
        "away_red_zone_known",
    }
)
_REQUIRED_RUSHING_COLUMNS = frozenset(
    {
        "game_id",
        "rush_off_epa_difference",
        "rush_def_epa_difference",
        "rush_success_difference",
        "explosive_run_rate_difference",
        "home_rushing_known",
        "away_rushing_known",
    }
)
_REQUIRED_DRIVE_COLUMNS = frozenset(
    {
        "game_id",
        "drive_off_epa_difference",
        "drive_def_epa_difference",
        "scoring_drive_rate_difference",
        "td_drive_rate_difference",
        "plays_per_drive_difference",
        "home_drive_efficiency_known",
        "away_drive_efficiency_known",
    }
)
_REQUIRED_SPECIAL_TEAMS_COLUMNS = frozenset(
    {
        "game_id",
        "fg_make_rate_difference",
        "punt_coverage_advantage",
        "punt_return_advantage",
        "punt_touchback_advantage",
        "home_special_teams_known",
        "away_special_teams_known",
    }
)
_REQUIRED_THIRD_DOWN_COLUMNS = frozenset(
    {
        "game_id",
        "third_down_off_epa_difference",
        "third_down_def_epa_difference",
        "third_down_conversion_difference",
        "third_down_stop_difference",
        "third_and_long_conversion_difference",
        "home_third_down_known",
        "away_third_down_known",
    }
)
_REQUIRED_PRESSURE_COLUMNS = frozenset(
    {
        "game_id",
        "pass_protection_advantage",
        "pressure_creation_advantage",
        "clean_dropback_advantage",
        "pressured_off_epa_difference",
        "pressured_def_epa_advantage",
        "home_pressure_known",
        "away_pressure_known",
    }
)
_REQUIRED_NEUTRAL_STATE_COLUMNS = frozenset(
    {
        "game_id",
        "neutral_off_epa_difference",
        "neutral_def_epa_difference",
        "neutral_success_difference",
        "neutral_yards_per_play_difference",
        "neutral_explosive_rate_difference",
        "home_neutral_state_known",
        "away_neutral_state_known",
    }
)

_REQUIRED_FIELD_POSITION_COLUMNS = frozenset(
    {
        "game_id",
        "off_start_field_position_advantage",
        "def_field_position_advantage",
        "short_field_rate_difference",
        "long_field_avoidance_advantage",
        "hidden_yards_field_position_advantage",
        "home_field_position_known",
        "away_field_position_known",
    }
)
_REQUIRED_FOURTH_DOWN_COLUMNS = frozenset(
    {
        "game_id",
        "fourth_down_off_epa_difference",
        "fourth_down_def_epa_difference",
        "fourth_down_conversion_difference",
        "fourth_down_stop_difference",
        "fourth_short_conversion_difference",
        "home_fourth_down_known",
        "away_fourth_down_known",
    }
)
_REQUIRED_EXPLOSIVE_SUPPRESSION_COLUMNS = frozenset(
    {
        "game_id",
        "explosive_off_rate_difference",
        "explosive_suppression_advantage",
        "chunk_off_rate_difference",
        "chunk_suppression_advantage",
        "explosive_yards_share_difference",
        "home_explosive_suppression_known",
        "away_explosive_suppression_known",
    }
)
_REQUIRED_TURNOVER_STABILITY_COLUMNS = frozenset(
    {
        "game_id",
        "turnover_protection_advantage",
        "takeaway_creation_advantage",
        "interception_protection_advantage",
        "interception_creation_advantage",
        "off_fumble_luck_advantage",
        "def_fumble_luck_advantage",
        "combined_fumble_recovery_luck",
        "home_turnover_stability_known",
        "away_turnover_stability_known",
    }
)
_REQUIRED_RECENT_FORM_COLUMNS = frozenset(
    {
        "game_id",
        "recent_off_epa_difference",
        "recent_def_epa_advantage",
        "off_epa_trend_difference",
        "def_epa_trend_advantage",
        "off_success_trend_difference",
        "def_success_trend_advantage",
        "home_recent_form_known",
        "away_recent_form_known",
    }
)
_REQUIRED_OPPONENT_ADJUSTED_COLUMNS = frozenset(
    {
        "game_id",
        "opponent_adjusted_off_epa_difference",
        "opponent_adjusted_def_epa_difference",
        "offensive_schedule_difficulty_advantage",
        "defensive_schedule_difficulty_advantage",
        "home_opponent_adjusted_known",
        "away_opponent_adjusted_known",
    }
)

_REQUIRED_PENALTY_DISCIPLINE_COLUMNS = frozenset(
    {
        "game_id",
        "penalty_yards_discipline_advantage",
        "penalty_rate_discipline_advantage",
        "offensive_penalty_discipline_advantage",
        "defensive_penalty_discipline_advantage",
        "home_penalty_discipline_known",
        "away_penalty_discipline_known",
    }
)

_REQUIRED_TRAVEL_FATIGUE_COLUMNS = frozenset(
    {
        "game_id",
        "away_travel_miles",
        "away_time_zone_shift_hours",
        "travel_geography_known",
    }
)

_REQUIRED_GAME_ENVIRONMENT_COLUMNS = frozenset(
    {
        "game_id",
        "temperature_f",
        "wind_mph",
        "weather_text",
        "roof_text",
        "indoor_or_closed_roof",
        "adverse_weather",
        "high_wind",
        "extreme_cold",
        "environment_known",
    }
)

_REQUIRED_FORECAST_WEATHER_COLUMNS = frozenset(
    {
        "game_id",
        "forecast_wind_mph",
        "research_only",
        "exact_forecast_vintage_known",
    }
)

_REQUIRED_PACE_TEMPO_COLUMNS = frozenset(
    {
        "game_id",
        "pace_play_volume_advantage",
        "pace_seconds_advantage",
        "tempo_index_advantage",
        "home_pace_tempo_known",
        "away_pace_tempo_known",
    }
)

_REQUIRED_PERFORMANCE_STABILITY_COLUMNS = frozenset(
    {
        "game_id",
        "stability_advantage",
        "recent_margin_advantage",
        "close_game_experience_advantage",
        "home_performance_stability_known",
        "away_performance_stability_known",
    }
)

_REQUIRED_FIRST_HALF_FORM_COLUMNS = frozenset(
    {
        "game_id",
        "first_half_off_epa_advantage",
        "first_half_def_epa_advantage",
        "first_half_play_volume_advantage",
        "home_first_half_form_known",
        "away_first_half_form_known",
    }
)

_REQUIRED_EXPLOSIVE_PLAY_COLUMNS = frozenset(
    {
        "game_id",
        "explosive_pass_rate_advantage",
        "explosive_rush_rate_advantage",
        "explosive_play_rate_advantage",
        "home_explosive_play_known",
        "away_explosive_play_known",
    }
)

_REQUIRED_PLAY_CONSISTENCY_COLUMNS = frozenset(
    {
        "game_id",
        "off_success_rate_advantage",
        "def_success_prevention_advantage",
        "success_rate_matchup_advantage",
        "negative_play_matchup_advantage",
        "home_play_consistency_known",
        "away_play_consistency_known",
    }
)






def run_experiments(
    schedule: pl.DataFrame,
    pgr: pl.DataFrame,
    experiments: list[ExperimentConfig],
    rest_features: pl.DataFrame | None = None,
    qb_features: pl.DataFrame | None = None,
    injury_features: pl.DataFrame | None = None,
    early_down_features: pl.DataFrame | None = None,
    turnover_features: pl.DataFrame | None = None,
    passing_features: pl.DataFrame | None = None,
    red_zone_features: pl.DataFrame | None = None,
    rushing_features: pl.DataFrame | None = None,
    drive_efficiency_features: pl.DataFrame | None = None,
    special_teams_features: pl.DataFrame | None = None,
    third_down_features: pl.DataFrame | None = None,
    pressure_features: pl.DataFrame | None = None,
    neutral_state_features: pl.DataFrame | None = None,
    field_position_features: pl.DataFrame | None = None,
    fourth_down_features: pl.DataFrame | None = None,
    explosive_suppression_features: pl.DataFrame | None = None,
    turnover_stability_features: pl.DataFrame | None = None,
    recent_form_features: pl.DataFrame | None = None,
    opponent_adjusted_features: pl.DataFrame | None = None,
    penalty_discipline_features: pl.DataFrame | None = None,
    travel_fatigue_features: pl.DataFrame | None = None,
    game_environment_features: pl.DataFrame | None = None,
    forecast_weather_features: pl.DataFrame | None = None,
    pace_tempo_features: pl.DataFrame | None = None,
    performance_stability_features: pl.DataFrame | None = None,
    first_half_form_features: pl.DataFrame | None = None,
    explosive_play_features: pl.DataFrame | None = None,
    play_consistency_features: pl.DataFrame | None = None,
) -> list[ExperimentResult]:
    validate_experiments(experiments)
    _validate_input(
        experiments,
        rest_features,
        qb_features,
        injury_features,
        early_down_features,
        turnover_features,
        passing_features,
        red_zone_features,
        rushing_features,
        drive_efficiency_features,
        special_teams_features,
        third_down_features,
        pressure_features,
        neutral_state_features,
        field_position_features,
        fourth_down_features,
        explosive_suppression_features,
        turnover_stability_features,
        recent_form_features,
        opponent_adjusted_features,
        penalty_discipline_features,
        travel_fatigue_features,
        game_environment_features,
        forecast_weather_features,
        pace_tempo_features,
        performance_stability_features,
        first_half_form_features,
        explosive_play_features,
        play_consistency_features,
    )

    results = [
        _run_one(
            schedule,
            pgr,
            rest_features,
            qb_features,
            injury_features,
            early_down_features,
            turnover_features,
            passing_features,
            red_zone_features,
            rushing_features,
            drive_efficiency_features,
            special_teams_features,
            third_down_features,
            pressure_features,
            neutral_state_features,
            field_position_features,
            fourth_down_features,
            explosive_suppression_features,
            turnover_stability_features,
            recent_form_features,
            opponent_adjusted_features,
            penalty_discipline_features,
            travel_fatigue_features,
            game_environment_features,
            forecast_weather_features,
            pace_tempo_features,
            performance_stability_features,
            first_half_form_features,
            explosive_play_features,
            play_consistency_features,
            config,
        )
        for config in experiments
    ]

    return sorted(
        results,
        key=lambda result: (
            result.selection_score,
            result.brier_score,
            result.log_loss,
            -result.winner_accuracy,
            result.name,
        ),
    )


def _run_one(
    schedule: pl.DataFrame,
    pgr: pl.DataFrame,
    rest_features: pl.DataFrame | None,
    qb_features: pl.DataFrame | None,
    injury_features: pl.DataFrame | None,
    early_down_features: pl.DataFrame | None,
    turnover_features: pl.DataFrame | None,
    passing_features: pl.DataFrame | None,
    red_zone_features: pl.DataFrame | None,
    rushing_features: pl.DataFrame | None,
    drive_efficiency_features: pl.DataFrame | None,
    special_teams_features: pl.DataFrame | None,
    third_down_features: pl.DataFrame | None,
    pressure_features: pl.DataFrame | None,
    neutral_state_features: pl.DataFrame | None,
    field_position_features: pl.DataFrame | None,
    fourth_down_features: pl.DataFrame | None,
    explosive_suppression_features: pl.DataFrame | None,
    turnover_stability_features: pl.DataFrame | None,
    recent_form_features: pl.DataFrame | None,
    opponent_adjusted_features: pl.DataFrame | None,
    penalty_discipline_features: pl.DataFrame | None,
    travel_fatigue_features: pl.DataFrame | None,
    game_environment_features: pl.DataFrame | None,
    forecast_weather_features: pl.DataFrame | None,
    pace_tempo_features: pl.DataFrame | None,
    performance_stability_features: pl.DataFrame | None,
    first_half_form_features: pl.DataFrame | None,
    explosive_play_features: pl.DataFrame | None,
    play_consistency_features: pl.DataFrame | None,
    config: ExperimentConfig,
) -> ExperimentResult:
    predictions = build_predictions(
        schedule,
        pgr,
        home_field_advantage=config.home_field_advantage,
        probability_scale=config.probability_scale,
    )
    predictions = _join_or_zero(predictions, rest_features, "rest_advantage")
    predictions = _join_or_zero(predictions, qb_features, "qb_rating_difference")
    predictions = _join_or_zero(
        predictions,
        injury_features,
        "injury_score_difference",
    )
    predictions = _join_early_down_or_zero(predictions, early_down_features)
    predictions = _join_turnovers_or_zero(predictions, turnover_features)
    predictions = _join_passing_or_zero(predictions, passing_features)
    predictions = _join_red_zone_or_zero(predictions, red_zone_features)
    predictions = _join_rushing_or_zero(predictions, rushing_features)
    predictions = _join_drive_or_zero(predictions, drive_efficiency_features)
    predictions = _join_special_teams_or_zero(
        predictions,
        special_teams_features,
    )
    predictions = _join_third_down_or_zero(predictions, third_down_features)
    predictions = _join_pressure_or_zero(predictions, pressure_features)
    predictions = _join_neutral_state_or_zero(
        predictions,
        neutral_state_features,
    )
    predictions = _join_field_position_or_zero(
        predictions,
        field_position_features,
    )
    predictions = _join_fourth_down_or_zero(
        predictions,
        fourth_down_features,
    )
    predictions = _join_explosive_suppression_or_zero(
        predictions,
        explosive_suppression_features,
    )
    predictions = _join_turnover_stability_or_zero(
        predictions,
        turnover_stability_features,
    )
    predictions = _join_recent_form_or_zero(
        predictions,
        recent_form_features,
    )
    predictions = _join_opponent_adjusted_or_zero(
        predictions,
        opponent_adjusted_features,
    )
    predictions = _join_penalty_discipline_or_zero(
        predictions,
        penalty_discipline_features,
    )

    predictions = _join_travel_fatigue_or_zero(
        predictions, travel_fatigue_features
    )
    predictions = _join_game_environment_or_zero(
        predictions,
        game_environment_features,
    )
    predictions = _join_forecast_weather_or_zero(
        predictions,
        forecast_weather_features,
    )
    predictions = _join_pace_tempo_or_zero(
        predictions,
        pace_tempo_features,
    )
    predictions = _join_performance_stability_or_zero(
        predictions,
        performance_stability_features,
    )
    predictions = _join_first_half_form_or_zero(
        predictions, first_half_form_features
    )
    predictions = _join_explosive_play_or_zero(
        predictions,
        explosive_play_features,
    )
    predictions = _join_play_consistency_or_zero(
        predictions,
        play_consistency_features,
    )
    predictions = (
        predictions.with_columns(
            (
                pl.col("rating_difference")
                + pl.col("rest_advantage") * config.rest_weight
                + pl.col("qb_rating_difference") * config.qb_weight
                - pl.col("injury_score_difference") * config.injury_weight
                + pl.col("early_down_off_epa_difference")
                * config.early_down_off_weight
                + pl.col("early_down_def_epa_difference")
                * config.early_down_def_weight
                + pl.col("early_down_success_difference")
                * config.early_down_success_weight
                + pl.col("interception_rate_difference")
                * config.turnover_int_weight
                + pl.col("fumble_lost_rate_difference")
                * config.turnover_fumble_weight
                + pl.col("pass_off_epa_difference")
                * config.pass_off_epa_weight
                + pl.col("pass_def_epa_difference")
                * config.pass_def_epa_weight
                + pl.col("pass_success_difference")
                * config.pass_success_weight
                + pl.col("off_sack_rate_advantage")
                * config.off_sack_weight
                + pl.col("def_sack_rate_advantage")
                * config.def_sack_weight
                + pl.col("explosive_pass_rate_difference")
                * config.explosive_pass_weight
                + pl.col("red_zone_off_epa_difference")
                * config.red_zone_off_epa_weight
                + pl.col("red_zone_def_epa_difference")
                * config.red_zone_def_epa_weight
                + pl.col("red_zone_success_difference")
                * config.red_zone_success_weight
                + pl.col("red_zone_td_rate_difference")
                * config.red_zone_td_rate_weight
                + pl.col("rush_off_epa_difference")
                * config.rush_off_epa_weight
                + pl.col("rush_def_epa_difference")
                * config.rush_def_epa_weight
                + pl.col("rush_success_difference")
                * config.rush_success_weight
                + pl.col("explosive_run_rate_difference")
                * config.explosive_run_weight
                + pl.col("drive_off_epa_difference")
                * config.drive_off_epa_weight
                + pl.col("drive_def_epa_difference")
                * config.drive_def_epa_weight
                + pl.col("scoring_drive_rate_difference")
                * config.scoring_drive_rate_weight
                + pl.col("td_drive_rate_difference")
                * config.td_drive_rate_weight
                + pl.col("plays_per_drive_difference")
                * config.plays_per_drive_weight
                + pl.col("fg_make_rate_difference")
                * config.fg_make_rate_weight
                + pl.col("punt_coverage_advantage")
                * config.punt_coverage_weight
                + pl.col("punt_return_advantage")
                * config.punt_return_weight
                + pl.col("punt_touchback_advantage")
                * config.punt_touchback_weight
                + pl.col("third_down_off_epa_difference")
                * config.third_down_off_epa_weight
                + pl.col("third_down_def_epa_difference")
                * config.third_down_def_epa_weight
                + pl.col("third_down_conversion_difference")
                * config.third_down_conversion_weight
                + pl.col("third_down_stop_difference")
                * config.third_down_stop_weight
                + pl.col("third_and_long_conversion_difference")
                * config.third_and_long_weight
                + pl.col("pass_protection_advantage")
                * config.pass_protection_weight
                + pl.col("pressure_creation_advantage")
                * config.pressure_creation_weight
                + pl.col("clean_dropback_advantage")
                * config.clean_dropback_weight
                + pl.col("pressured_off_epa_difference")
                * config.pressured_off_epa_weight
                + pl.col("pressured_def_epa_advantage")
                * config.pressured_def_epa_weight
                + pl.col("neutral_off_epa_difference")
                * config.neutral_off_epa_weight
                + pl.col("neutral_def_epa_difference")
                * config.neutral_def_epa_weight
                + pl.col("neutral_success_difference")
                * config.neutral_success_weight
                + pl.col("neutral_yards_per_play_difference")
                * config.neutral_yards_per_play_weight
                + pl.col("neutral_explosive_rate_difference")
                * config.neutral_explosive_weight
                + pl.col("off_start_field_position_advantage")
                * config.off_start_field_position_weight
                + pl.col("def_field_position_advantage")
                * config.def_field_position_weight
                + pl.col("short_field_rate_difference")
                * config.short_field_rate_weight
                + pl.col("long_field_avoidance_advantage")
                * config.long_field_avoidance_weight
                + pl.col("hidden_yards_field_position_advantage")
                * config.hidden_yards_field_position_weight
                + pl.col("fourth_down_off_epa_difference")
                * config.fourth_down_off_epa_weight
                + pl.col("fourth_down_def_epa_difference")
                * config.fourth_down_def_epa_weight
                + pl.col("fourth_down_conversion_difference")
                * config.fourth_down_conversion_weight
                + pl.col("fourth_down_stop_difference")
                * config.fourth_down_stop_weight
                + pl.col("fourth_short_conversion_difference")
                * config.fourth_short_conversion_weight
                + pl.col("explosive_off_rate_difference")
                * config.explosive_off_rate_weight
                + pl.col("explosive_suppression_advantage")
                * config.explosive_suppression_weight
                + pl.col("chunk_off_rate_difference")
                * config.chunk_off_rate_weight
                + pl.col("chunk_suppression_advantage")
                * config.chunk_suppression_weight
                + pl.col("explosive_yards_share_difference")
                * config.explosive_yards_share_weight
                + pl.col("turnover_protection_advantage")
                * config.turnover_protection_weight
                + pl.col("takeaway_creation_advantage")
                * config.takeaway_creation_weight
                + pl.col("interception_protection_advantage")
                * config.interception_protection_weight
                + pl.col("interception_creation_advantage")
                * config.interception_creation_weight
                + pl.col("off_fumble_luck_advantage")
                * config.off_fumble_luck_weight
                + pl.col("def_fumble_luck_advantage")
                * config.def_fumble_luck_weight
                + pl.col("combined_fumble_recovery_luck")
                * config.combined_fumble_luck_weight
                + pl.col("recent_off_epa_difference")
                * config.recent_off_epa_weight
                + pl.col("recent_def_epa_advantage")
                * config.recent_def_epa_weight
                + pl.col("off_epa_trend_difference")
                * config.off_epa_trend_weight
                + pl.col("def_epa_trend_advantage")
                * config.def_epa_trend_weight
                + pl.col("off_success_trend_difference")
                * config.off_success_trend_weight
                + pl.col("def_success_trend_advantage")
                * config.def_success_trend_weight
                + pl.col("opponent_adjusted_off_epa_difference")
                * config.opponent_adjusted_off_epa_weight
                + pl.col("opponent_adjusted_def_epa_difference")
                * config.opponent_adjusted_def_epa_weight
                + pl.col("offensive_schedule_difficulty_advantage")
                * config.offensive_schedule_difficulty_weight
                + pl.col("defensive_schedule_difficulty_advantage")
                * config.defensive_schedule_difficulty_weight
                + pl.col("travel_miles_advantage")
                * config.travel_miles_weight
                + pl.col("travel_time_zone_advantage")
                * config.travel_time_zone_weight
                + pl.col("adverse_weather_advantage")
                * config.adverse_weather_weight
                + pl.col("indoor_environment_advantage")
                * config.indoor_environment_weight
                + pl.col("high_wind_advantage")
                * config.high_wind_weight
                + pl.col("extreme_cold_advantage")
                * config.extreme_cold_weight
                + pl.col("forecast_high_wind_advantage")
                * config.forecast_high_wind_weight
                + pl.col("pace_play_volume_advantage").fill_nan(0.0).fill_null(0.0)
                * config.pace_play_volume_weight
                + pl.col("pace_seconds_advantage").fill_nan(0.0).fill_null(0.0)
                * config.pace_seconds_weight
                + pl.col("tempo_index_advantage").fill_nan(0.0).fill_null(0.0)
                * config.tempo_index_weight
                + pl.col("stability_advantage").fill_nan(0.0).fill_null(0.0)
                * config.performance_stability_weight
                + pl.col("recent_margin_advantage").fill_nan(0.0).fill_null(0.0)
                * config.recent_margin_weight
                + pl.col("close_game_experience_advantage").fill_nan(0.0).fill_null(0.0)
                * config.close_game_experience_weight
                + pl.col("first_half_off_epa_advantage").fill_nan(0.0).fill_null(0.0)
                * config.first_half_off_epa_weight
                + pl.col("first_half_def_epa_advantage").fill_nan(0.0).fill_null(0.0)
                * config.first_half_def_epa_weight
                + pl.col("first_half_play_volume_advantage").fill_nan(0.0).fill_null(0.0)
                * config.first_half_play_volume_weight
                + pl.col("explosive_pass_rate_advantage").fill_nan(0.0).fill_null(0.0)
                * config.explosive_pass_rate_weight
                + pl.col("explosive_rush_rate_advantage").fill_nan(0.0).fill_null(0.0)
                * config.explosive_rush_rate_weight
                + pl.col("explosive_play_rate_advantage").fill_nan(0.0).fill_null(0.0)
                * config.explosive_play_rate_weight
                + pl.col("off_success_rate_advantage").fill_nan(0.0).fill_null(0.0)
                * config.off_success_rate_weight
                + pl.col("def_success_prevention_advantage").fill_nan(0.0).fill_null(0.0)
                * config.def_success_prevention_weight
                + pl.col("success_rate_matchup_advantage").fill_nan(0.0).fill_null(0.0)
                * config.success_rate_matchup_weight
                + pl.col("negative_play_matchup_advantage").fill_nan(0.0).fill_null(0.0)
                * config.negative_play_matchup_weight
                + pl.col("penalty_yards_discipline_advantage")
                * config.penalty_yards_discipline_weight
                + pl.col("penalty_rate_discipline_advantage")
                * config.penalty_rate_discipline_weight
                + pl.col("offensive_penalty_discipline_advantage")
                * config.offensive_penalty_discipline_weight
                + pl.col("defensive_penalty_discipline_advantage")
                * config.defensive_penalty_discipline_weight
            ).alias("rating_difference")
        )
        .with_columns(
            (
                pl.col("rating_difference") * config.margin_scale
                + config.margin_intercept
            ).alias("expected_home_margin"),
            pl.col("rating_difference")
            .map_elements(
                lambda value: home_win_probability(
                    value,
                    scale=config.probability_scale,
                ),
                return_dtype=pl.Float64,
            )
            .alias("home_win_probability"),
        )
        .with_columns(
            (1.0 - pl.col("home_win_probability")).alias(
                "away_win_probability"
            ),
            pl.when(pl.col("rating_difference") >= 0)
            .then(pl.col("home_team"))
            .otherwise(pl.col("away_team"))
            .alias("predicted_winner"),
            pl.col("home_win_probability")
            .map_elements(
                classify_confidence,
                return_dtype=pl.String,
            )
            .alias("confidence"),
            pl.lit(config.name).alias("model_version"),
        )
    )

    for column, label in (
        ("rest_advantage", "Rest"),
        ("qb_rating_difference", "QB"),
        ("injury_score_difference", "Injury"),
        ("early_down_off_epa_difference", "Early-down offense"),
        ("early_down_def_epa_difference", "Early-down defense"),
        ("early_down_success_difference", "Early-down success"),
        ("interception_rate_difference", "Turnover interception"),
        ("fumble_lost_rate_difference", "Turnover fumble"),
        ("pass_off_epa_difference", "Passing offense EPA"),
        ("pass_def_epa_difference", "Passing defense EPA"),
        ("pass_success_difference", "Passing success"),
        ("off_sack_rate_advantage", "Offensive sack"),
        ("def_sack_rate_advantage", "Defensive sack"),
        ("explosive_pass_rate_difference", "Explosive pass"),
        ("red_zone_off_epa_difference", "Red-zone offense EPA"),
        ("red_zone_def_epa_difference", "Red-zone defense EPA"),
        ("red_zone_success_difference", "Red-zone success"),
        ("red_zone_td_rate_difference", "Red-zone TD rate"),
        ("rush_off_epa_difference", "Rushing offense EPA"),
        ("rush_def_epa_difference", "Rushing defense EPA"),
        ("rush_success_difference", "Rushing success"),
        ("explosive_run_rate_difference", "Explosive run"),
        ("drive_off_epa_difference", "Drive offense EPA"),
        ("drive_def_epa_difference", "Drive defense EPA"),
        ("scoring_drive_rate_difference", "Scoring drive rate"),
        ("td_drive_rate_difference", "TD drive rate"),
        ("plays_per_drive_difference", "Plays per drive"),
        ("fg_make_rate_difference", "Field-goal make rate"),
        ("punt_coverage_advantage", "Punt coverage"),
        ("punt_return_advantage", "Punt return"),
        ("punt_touchback_advantage", "Punt touchback"),
        ("third_down_off_epa_difference", "Third-down offense EPA"),
        ("third_down_def_epa_difference", "Third-down defense EPA"),
        ("third_down_conversion_difference", "Third-down conversion"),
        ("third_down_stop_difference", "Third-down stop"),
        ("third_and_long_conversion_difference", "Third-and-long conversion"),
        ("pass_protection_advantage", "Pass protection"),
        ("pressure_creation_advantage", "Pressure creation"),
        ("clean_dropback_advantage", "Clean dropback"),
        ("pressured_off_epa_difference", "Pressured offense EPA"),
        ("pressured_def_epa_advantage", "Pressured defense EPA"),
        ("neutral_off_epa_difference", "Neutral-state offense EPA"),
        ("neutral_def_epa_difference", "Neutral-state defense EPA"),
        ("neutral_success_difference", "Neutral-state success"),
        ("neutral_yards_per_play_difference", "Neutral-state yards/play"),
        ("neutral_explosive_rate_difference", "Neutral-state explosive rate"),
        ("off_start_field_position_advantage", "Offensive start field position"),
        ("def_field_position_advantage", "Defensive field position"),
        ("short_field_rate_difference", "Short-field rate"),
        ("long_field_avoidance_advantage", "Long-field avoidance"),
        ("hidden_yards_field_position_advantage", "Hidden-yards field position"),
        ("fourth_down_off_epa_difference", "Fourth-down offense EPA"),
        ("fourth_down_def_epa_difference", "Fourth-down defense EPA"),
        ("fourth_down_conversion_difference", "Fourth-down conversion"),
        ("fourth_down_stop_difference", "Fourth-down stop"),
        ("fourth_short_conversion_difference", "Fourth-down short conversion"),
    ):
        if predictions[column].null_count():
            raise ValueError(
                f"{label} features do not cover every prediction game."
            )

    backtest, _ = evaluate_predictions(predictions, schedule)
    score = selection_score(
        winner_accuracy=backtest.winner_accuracy,
        brier_score=backtest.brier_score,
        log_loss=backtest.log_loss,
        margin_rmse=backtest.margin_rmse,
    )
    return ExperimentResult.create(
        config=config,
        season=backtest.season,
        games_evaluated=backtest.games_evaluated,
        winner_accuracy=backtest.winner_accuracy,
        brier_score=backtest.brier_score,
        log_loss=backtest.log_loss,
        margin_mae=backtest.margin_mae,
        margin_rmse=backtest.margin_rmse,
        selection_score=score,
    )


def _join_or_zero(
    predictions: pl.DataFrame,
    features: pl.DataFrame | None,
    column: str,
) -> pl.DataFrame:
    if features is None:
        return predictions.with_columns(pl.lit(0.0).alias(column))
    return predictions.join(
        features.select("game_id", column),
        on="game_id",
        how="left",
        validate="1:1",
    )


def _neutralized_join(
    predictions: pl.DataFrame,
    features: pl.DataFrame | None,
    *,
    columns: list[str],
    known_columns: tuple[str, str],
) -> pl.DataFrame:
    if features is None:
        return predictions.with_columns(
            *[pl.lit(0.0).alias(column) for column in columns]
        )

    joined = predictions.join(
        features.select("game_id", *columns, *known_columns),
        on="game_id",
        how="left",
        validate="1:1",
    )
    known = (
        pl.col(known_columns[0]).fill_null(False)
        & pl.col(known_columns[1]).fill_null(False)
    )
    return joined.with_columns(
        *[
            pl.when(known)
            .then(pl.col(column))
            .otherwise(0.0)
            .fill_null(0.0)
            .alias(column)
            for column in columns
        ]
    )


def _join_early_down_or_zero(predictions, features):
    return _neutralized_join(
        predictions,
        features,
        columns=[
            "early_down_off_epa_difference",
            "early_down_def_epa_difference",
            "early_down_success_difference",
        ],
        known_columns=("home_early_down_known", "away_early_down_known"),
    )


def _join_turnovers_or_zero(predictions, features):
    return _neutralized_join(
        predictions,
        features,
        columns=[
            "interception_rate_difference",
            "fumble_lost_rate_difference",
        ],
        known_columns=("home_turnover_known", "away_turnover_known"),
    )


def _join_passing_or_zero(predictions, features):
    return _neutralized_join(
        predictions,
        features,
        columns=[
            "pass_off_epa_difference",
            "pass_def_epa_difference",
            "pass_success_difference",
            "off_sack_rate_advantage",
            "def_sack_rate_advantage",
            "explosive_pass_rate_difference",
        ],
        known_columns=("home_passing_known", "away_passing_known"),
    )


def _join_red_zone_or_zero(predictions, features):
    return _neutralized_join(
        predictions,
        features,
        columns=[
            "red_zone_off_epa_difference",
            "red_zone_def_epa_difference",
            "red_zone_success_difference",
            "red_zone_td_rate_difference",
        ],
        known_columns=("home_red_zone_known", "away_red_zone_known"),
    )


def _join_rushing_or_zero(predictions, features):
    return _neutralized_join(
        predictions,
        features,
        columns=[
            "rush_off_epa_difference",
            "rush_def_epa_difference",
            "rush_success_difference",
            "explosive_run_rate_difference",
        ],
        known_columns=("home_rushing_known", "away_rushing_known"),
    )


def _join_drive_or_zero(predictions, features):
    return _neutralized_join(
        predictions,
        features,
        columns=[
            "drive_off_epa_difference",
            "drive_def_epa_difference",
            "scoring_drive_rate_difference",
            "td_drive_rate_difference",
            "plays_per_drive_difference",
        ],
        known_columns=(
            "home_drive_efficiency_known",
            "away_drive_efficiency_known",
        ),
    )


def _join_special_teams_or_zero(predictions, features):
    return _neutralized_join(
        predictions,
        features,
        columns=[
            "fg_make_rate_difference",
            "punt_coverage_advantage",
            "punt_return_advantage",
            "punt_touchback_advantage",
        ],
        known_columns=(
            "home_special_teams_known",
            "away_special_teams_known",
        ),
    )


def _join_third_down_or_zero(predictions, features):
    return _neutralized_join(
        predictions,
        features,
        columns=[
            "third_down_off_epa_difference",
            "third_down_def_epa_difference",
            "third_down_conversion_difference",
            "third_down_stop_difference",
            "third_and_long_conversion_difference",
        ],
        known_columns=("home_third_down_known", "away_third_down_known"),
    )


def _join_pressure_or_zero(predictions, features):
    return _neutralized_join(
        predictions,
        features,
        columns=[
            "pass_protection_advantage",
            "pressure_creation_advantage",
            "clean_dropback_advantage",
            "pressured_off_epa_difference",
            "pressured_def_epa_advantage",
        ],
        known_columns=("home_pressure_known", "away_pressure_known"),
    )


def _join_neutral_state_or_zero(predictions, features):
    return _neutralized_join(
        predictions,
        features,
        columns=[
            "neutral_off_epa_difference",
            "neutral_def_epa_difference",
            "neutral_success_difference",
            "neutral_yards_per_play_difference",
            "neutral_explosive_rate_difference",
        ],
        known_columns=(
            "home_neutral_state_known",
            "away_neutral_state_known",
        ),
    )


def _join_field_position_or_zero(predictions, features):
    return _neutralized_join(
        predictions,
        features,
        columns=[
            "off_start_field_position_advantage",
            "def_field_position_advantage",
            "short_field_rate_difference",
            "long_field_avoidance_advantage",
            "hidden_yards_field_position_advantage",
        ],
        known_columns=(
            "home_field_position_known",
            "away_field_position_known",
        ),
    )


def _join_fourth_down_or_zero(predictions, features):
    return _neutralized_join(
        predictions,
        features,
        columns=[
            "fourth_down_off_epa_difference",
            "fourth_down_def_epa_difference",
            "fourth_down_conversion_difference",
            "fourth_down_stop_difference",
            "fourth_short_conversion_difference",
        ],
        known_columns=(
            "home_fourth_down_known",
            "away_fourth_down_known",
        ),
    )


def _join_explosive_suppression_or_zero(predictions, features):
    return _neutralized_join(
        predictions,
        features,
        columns=[
            "explosive_off_rate_difference",
            "explosive_suppression_advantage",
            "chunk_off_rate_difference",
            "chunk_suppression_advantage",
            "explosive_yards_share_difference",
        ],
        known_columns=(
            "home_explosive_suppression_known",
            "away_explosive_suppression_known",
        ),
    )


def _join_turnover_stability_or_zero(predictions, features):
    return _neutralized_join(
        predictions,
        features,
        columns=[
            "turnover_protection_advantage",
            "takeaway_creation_advantage",
            "interception_protection_advantage",
            "interception_creation_advantage",
            "off_fumble_luck_advantage",
            "def_fumble_luck_advantage",
            "combined_fumble_recovery_luck",
        ],
        known_columns=(
            "home_turnover_stability_known",
            "away_turnover_stability_known",
        ),
    )


def _join_recent_form_or_zero(predictions, features):
    return _neutralized_join(
        predictions,
        features,
        columns=[
            "recent_off_epa_difference",
            "recent_def_epa_advantage",
            "off_epa_trend_difference",
            "def_epa_trend_advantage",
            "off_success_trend_difference",
            "def_success_trend_advantage",
        ],
        known_columns=(
            "home_recent_form_known",
            "away_recent_form_known",
        ),
    )


def _join_play_consistency_or_zero(predictions, features):
    columns = [
        "off_success_rate_advantage",
        "def_success_prevention_advantage",
        "success_rate_matchup_advantage",
        "negative_play_matchup_advantage",
    ]
    if features is None:
        return predictions.with_columns(
            *[pl.lit(0.0).alias(column) for column in columns]
        )
    joined = predictions.join(
        features.select(
            "game_id", *columns,
            "home_play_consistency_known",
            "away_play_consistency_known",
        ),
        on="game_id", how="left",
    )
    known = (
        pl.col("home_play_consistency_known").fill_null(False)
        & pl.col("away_play_consistency_known").fill_null(False)
    )
    return joined.with_columns(
        *[
            pl.when(known & pl.col(column).is_finite().fill_null(False))
            .then(pl.col(column)).otherwise(0.0).alias(column)
            for column in columns
        ]
    )


def _join_explosive_play_or_zero(predictions, features):
    columns = [
        "explosive_pass_rate_advantage",
        "explosive_rush_rate_advantage",
        "explosive_play_rate_advantage",
    ]
    if features is None:
        return predictions.with_columns(
            *[pl.lit(0.0).alias(column) for column in columns]
        )
    joined = predictions.join(
        features.select(
            "game_id", *columns,
            "home_explosive_play_known",
            "away_explosive_play_known",
        ),
        on="game_id", how="left",
    )
    known = (
        pl.col("home_explosive_play_known").fill_null(False)
        & pl.col("away_explosive_play_known").fill_null(False)
    )
    return joined.with_columns(
        *[
            pl.when(known & pl.col(column).is_finite().fill_null(False))
            .then(pl.col(column)).otherwise(0.0).alias(column)
            for column in columns
        ]
    )


def _join_first_half_form_or_zero(predictions, features):
    columns = [
        "first_half_off_epa_advantage",
        "first_half_def_epa_advantage",
        "first_half_play_volume_advantage",
    ]
    if features is None:
        return predictions.with_columns(
            *[pl.lit(0.0).alias(column) for column in columns]
        )
    joined = predictions.join(
        features.select(
            "game_id", *columns,
            "home_first_half_form_known",
            "away_first_half_form_known",
        ),
        on="game_id", how="left",
    )
    known = (
        pl.col("home_first_half_form_known").fill_null(False)
        & pl.col("away_first_half_form_known").fill_null(False)
    )
    return joined.with_columns(
        *[
            pl.when(known & pl.col(column).is_finite().fill_null(False))
            .then(pl.col(column))
            .otherwise(0.0)
            .alias(column)
            for column in columns
        ]
    )


def _join_performance_stability_or_zero(predictions, features):
    if features is None:
        return predictions.with_columns(
            pl.lit(0.0).alias("stability_advantage"),
            pl.lit(0.0).alias("recent_margin_advantage"),
            pl.lit(0.0).alias("close_game_experience_advantage"),
        )

    return (
        predictions.join(
            features.select(
                "game_id",
                "stability_advantage",
                "recent_margin_advantage",
                "close_game_experience_advantage",
                "home_performance_stability_known",
                "away_performance_stability_known",
            ),
            on="game_id",
            how="left",
        )
        .with_columns(
            pl.when(
                pl.col("home_performance_stability_known")
                .fill_null(False)
                & pl.col("away_performance_stability_known")
                .fill_null(False)
            )
            .then(
                pl.when(
                    pl.col("stability_advantage")
                    .is_finite()
                    .fill_null(False)
                )
                .then(pl.col("stability_advantage"))
                .otherwise(0.0)
            )
            .otherwise(0.0)
            .alias("stability_advantage"),
            pl.when(
                pl.col("home_performance_stability_known")
                .fill_null(False)
                & pl.col("away_performance_stability_known")
                .fill_null(False)
            )
            .then(
                pl.when(
                    pl.col("recent_margin_advantage")
                    .is_finite()
                    .fill_null(False)
                )
                .then(pl.col("recent_margin_advantage"))
                .otherwise(0.0)
            )
            .otherwise(0.0)
            .alias("recent_margin_advantage"),
            pl.when(
                pl.col("home_performance_stability_known")
                .fill_null(False)
                & pl.col("away_performance_stability_known")
                .fill_null(False)
            )
            .then(
                pl.when(
                    pl.col("close_game_experience_advantage")
                    .is_finite()
                    .fill_null(False)
                )
                .then(pl.col("close_game_experience_advantage"))
                .otherwise(0.0)
            )
            .otherwise(0.0)
            .alias("close_game_experience_advantage"),
        )
    )


def _join_pace_tempo_or_zero(predictions, features):
    if features is None:
        return predictions.with_columns(
            pl.lit(0.0).alias("pace_play_volume_advantage"),
            pl.lit(0.0).alias("pace_seconds_advantage"),
            pl.lit(0.0).alias("tempo_index_advantage"),
        )
    return (
        predictions.join(
            features.select(
                "game_id",
                "pace_play_volume_advantage",
                "pace_seconds_advantage",
                "tempo_index_advantage",
                "home_pace_tempo_known",
                "away_pace_tempo_known",
            ),
            on="game_id",
            how="left",
        )
        .with_columns(
            pl.when(pl.col("home_pace_tempo_known").fill_null(False) & pl.col("away_pace_tempo_known").fill_null(False))
            .then(pl.col("pace_play_volume_advantage").fill_nan(0.0).fill_null(0.0).fill_null(0.0))
            .otherwise(0.0).alias("pace_play_volume_advantage"),
            pl.when(pl.col("home_pace_tempo_known").fill_null(False) & pl.col("away_pace_tempo_known").fill_null(False))
            .then(pl.col("pace_seconds_advantage").fill_nan(0.0).fill_null(0.0).fill_null(0.0))
            .otherwise(0.0).alias("pace_seconds_advantage"),
            pl.when(pl.col("home_pace_tempo_known").fill_null(False) & pl.col("away_pace_tempo_known").fill_null(False))
            .then(pl.col("tempo_index_advantage").fill_nan(0.0).fill_null(0.0).fill_null(0.0))
            .otherwise(0.0).alias("tempo_index_advantage"),
        )
    )


def _join_forecast_weather_or_zero(predictions, features):
    if features is None:
        return predictions.with_columns(
            pl.lit(0.0).alias("forecast_high_wind_advantage")
        )
    return predictions.join(
        features.select(
            "game_id", "forecast_wind_mph",
            "research_only", "exact_forecast_vintage_known",
        ),
        on="game_id", how="left",
    ).with_columns(
        pl.when(pl.col("forecast_wind_mph").is_not_null())
        .then((pl.col("forecast_wind_mph") >= 15.0).cast(pl.Float64))
        .otherwise(0.0)
        .alias("forecast_high_wind_advantage")
    )


def _join_game_environment_or_zero(predictions, features):
    if features is None:
        return predictions.with_columns(
            pl.lit(0.0).alias("adverse_weather_advantage"),
            pl.lit(0.0).alias("indoor_environment_advantage"),
            pl.lit(0.0).alias("high_wind_advantage"),
            pl.lit(0.0).alias("extreme_cold_advantage"),
        )

    joined = predictions.join(
        features.select(
            "game_id", "temperature_f", "wind_mph", "weather_text",
            "roof_text", "indoor_or_closed_roof", "adverse_weather",
            "high_wind", "extreme_cold", "environment_known",
        ),
        on="game_id", how="left",
    )
    weather_observed = (
        pl.col("temperature_f").is_not_null()
        | pl.col("wind_mph").is_not_null()
        | pl.col("weather_text").is_not_null()
    )
    return joined.with_columns(
        pl.when(pl.col("environment_known").fill_null(False) & weather_observed)
        .then(pl.col("adverse_weather").fill_null(False).cast(pl.Float64))
        .otherwise(0.0).alias("adverse_weather_advantage"),
        pl.when(pl.col("roof_text").is_not_null())
        .then(pl.col("indoor_or_closed_roof").fill_null(False).cast(pl.Float64))
        .otherwise(0.0).alias("indoor_environment_advantage"),
        pl.when(pl.col("wind_mph").is_not_null())
        .then(pl.col("high_wind").fill_null(False).cast(pl.Float64))
        .otherwise(0.0).alias("high_wind_advantage"),
        pl.when(pl.col("temperature_f").is_not_null())
        .then(pl.col("extreme_cold").fill_null(False).cast(pl.Float64))
        .otherwise(0.0).alias("extreme_cold_advantage"),
    )


def _join_travel_fatigue_or_zero(predictions, features):
    if features is None:
        return predictions.with_columns(
            pl.lit(0.0).alias("travel_miles_advantage"),
            pl.lit(0.0).alias("travel_time_zone_advantage"),
        )
    return (
        predictions.join(
            features.select(
                "game_id",
                "away_travel_miles",
                "away_time_zone_shift_hours",
                "travel_geography_known",
            ),
            on="game_id",
            how="left",
        )
        .with_columns(
            pl.when(pl.col("travel_geography_known").fill_null(False))
            .then(-pl.col("away_travel_miles").fill_null(0.0) / 1000.0)
            .otherwise(0.0)
            .alias("travel_miles_advantage"),
            pl.when(pl.col("travel_geography_known").fill_null(False))
            .then(-pl.col("away_time_zone_shift_hours").fill_null(0.0))
            .otherwise(0.0)
            .alias("travel_time_zone_advantage"),
        )
    )


def _join_opponent_adjusted_or_zero(predictions, features):
    columns = [
        "opponent_adjusted_off_epa_difference",
        "opponent_adjusted_def_epa_difference",
        "offensive_schedule_difficulty_advantage",
        "defensive_schedule_difficulty_advantage",
    ]
    if features is None:
        return predictions.with_columns(
            *[pl.lit(0.0).alias(column) for column in columns]
        )
    return (
        predictions.join(
            features.select("game_id", *columns),
            on="game_id",
            how="left",
        )
        .with_columns(*[pl.col(column).fill_null(0.0) for column in columns])
    )


def _join_penalty_discipline_or_zero(predictions, features):
    columns = [
        "penalty_yards_discipline_advantage",
        "penalty_rate_discipline_advantage",
        "offensive_penalty_discipline_advantage",
        "defensive_penalty_discipline_advantage",
    ]
    if features is None:
        return predictions.with_columns(
            *[pl.lit(0.0).alias(column) for column in columns]
        )
    return (
        predictions.join(
            features.select("game_id", *columns),
            on="game_id",
            how="left",
        )
        .with_columns(
            *[
                pl.col(column).fill_null(0.0).alias(column)
                for column in columns
            ]
        )
    )


def _validate_input(
    experiments,
    rest_features,
    qb_features,
    injury_features,
    early_down_features,
    turnover_features,
    passing_features,
    red_zone_features,
    rushing_features,
    drive_efficiency_features,
    special_teams_features,
    third_down_features,
    pressure_features,
    neutral_state_features,
    field_position_features,
    fourth_down_features,
    explosive_suppression_features,
    turnover_stability_features,
    recent_form_features,
    opponent_adjusted_features,
    penalty_discipline_features,
    travel_fatigue_features,
    game_environment_features,
    forecast_weather_features,
    pace_tempo_features,
    performance_stability_features,
    first_half_form_features,
    explosive_play_features,
    play_consistency_features,
) -> None:
    _validate_feature(
        experiments,
        rest_features,
        _REQUIRED_REST_COLUMNS,
        "rest_weight",
        "Rest",
    )
    _validate_feature(
        experiments,
        qb_features,
        _REQUIRED_QB_COLUMNS,
        "qb_weight",
        "QB",
    )
    _validate_feature(
        experiments,
        injury_features,
        _REQUIRED_INJURY_COLUMNS,
        "injury_weight",
        "Injury",
    )

    _validate_group(
        any(
            e.early_down_off_weight != 0.0
            or e.early_down_def_weight != 0.0
            or e.early_down_success_weight != 0.0
            for e in experiments
        ),
        early_down_features,
        _REQUIRED_EARLY_DOWN_COLUMNS,
        "Early-down",
    )
    _validate_group(
        any(
            e.turnover_int_weight != 0.0
            or e.turnover_fumble_weight != 0.0
            for e in experiments
        ),
        turnover_features,
        _REQUIRED_TURNOVER_COLUMNS,
        "Turnover",
    )
    _validate_group(
        any(
            e.pass_off_epa_weight != 0.0
            or e.pass_def_epa_weight != 0.0
            or e.pass_success_weight != 0.0
            or e.off_sack_weight != 0.0
            or e.def_sack_weight != 0.0
            or e.explosive_pass_weight != 0.0
            for e in experiments
        ),
        passing_features,
        _REQUIRED_PASSING_COLUMNS,
        "Passing",
    )
    _validate_group(
        any(
            e.red_zone_off_epa_weight != 0.0
            or e.red_zone_def_epa_weight != 0.0
            or e.red_zone_success_weight != 0.0
            or e.red_zone_td_rate_weight != 0.0
            for e in experiments
        ),
        red_zone_features,
        _REQUIRED_RED_ZONE_COLUMNS,
        "Red-zone",
    )
    _validate_group(
        any(
            e.rush_off_epa_weight != 0.0
            or e.rush_def_epa_weight != 0.0
            or e.rush_success_weight != 0.0
            or e.explosive_run_weight != 0.0
            for e in experiments
        ),
        rushing_features,
        _REQUIRED_RUSHING_COLUMNS,
        "Rushing",
    )
    _validate_group(
        any(
            e.drive_off_epa_weight != 0.0
            or e.drive_def_epa_weight != 0.0
            or e.scoring_drive_rate_weight != 0.0
            or e.td_drive_rate_weight != 0.0
            or e.plays_per_drive_weight != 0.0
            for e in experiments
        ),
        drive_efficiency_features,
        _REQUIRED_DRIVE_COLUMNS,
        "Drive-efficiency",
    )
    _validate_group(
        any(
            e.fg_make_rate_weight != 0.0
            or e.punt_coverage_weight != 0.0
            or e.punt_return_weight != 0.0
            or e.punt_touchback_weight != 0.0
            for e in experiments
        ),
        special_teams_features,
        _REQUIRED_SPECIAL_TEAMS_COLUMNS,
        "Special-teams",
    )
    _validate_group(
        any(
            e.third_down_off_epa_weight != 0.0
            or e.third_down_def_epa_weight != 0.0
            or e.third_down_conversion_weight != 0.0
            or e.third_down_stop_weight != 0.0
            or e.third_and_long_weight != 0.0
            for e in experiments
        ),
        third_down_features,
        _REQUIRED_THIRD_DOWN_COLUMNS,
        "Third-down",
    )
    _validate_group(
        any(
            e.pass_protection_weight != 0.0
            or e.pressure_creation_weight != 0.0
            or e.clean_dropback_weight != 0.0
            or e.pressured_off_epa_weight != 0.0
            or e.pressured_def_epa_weight != 0.0
            for e in experiments
        ),
        pressure_features,
        _REQUIRED_PRESSURE_COLUMNS,
        "Pressure",
    )
    _validate_group(
        any(
            e.neutral_off_epa_weight != 0.0
            or e.neutral_def_epa_weight != 0.0
            or e.neutral_success_weight != 0.0
            or e.neutral_yards_per_play_weight != 0.0
            or e.neutral_explosive_weight != 0.0
            for e in experiments
        ),
        neutral_state_features,
        _REQUIRED_NEUTRAL_STATE_COLUMNS,
        "Neutral-state",
    )
    _validate_group(
        any(
            e.off_start_field_position_weight != 0.0
            or e.def_field_position_weight != 0.0
            or e.short_field_rate_weight != 0.0
            or e.long_field_avoidance_weight != 0.0
            or e.hidden_yards_field_position_weight != 0.0
            for e in experiments
        ),
        field_position_features,
        _REQUIRED_FIELD_POSITION_COLUMNS,
        "Field-position",
    )
    _validate_group(
        any(
            e.fourth_down_off_epa_weight != 0.0
            or e.fourth_down_def_epa_weight != 0.0
            or e.fourth_down_conversion_weight != 0.0
            or e.fourth_down_stop_weight != 0.0
            or e.fourth_short_conversion_weight != 0.0
            for e in experiments
        ),
        fourth_down_features,
        _REQUIRED_FOURTH_DOWN_COLUMNS,
        "Fourth-down",
    )
    _validate_group(
        any(
            e.explosive_off_rate_weight != 0.0
            or e.explosive_suppression_weight != 0.0
            or e.chunk_off_rate_weight != 0.0
            or e.chunk_suppression_weight != 0.0
            or e.explosive_yards_share_weight != 0.0
            for e in experiments
        ),
        explosive_suppression_features,
        _REQUIRED_EXPLOSIVE_SUPPRESSION_COLUMNS,
        "Explosive-suppression",
    )
    _validate_group(
        any(
            e.turnover_protection_weight != 0.0
            or e.takeaway_creation_weight != 0.0
            or e.interception_protection_weight != 0.0
            or e.interception_creation_weight != 0.0
            or e.off_fumble_luck_weight != 0.0
            or e.def_fumble_luck_weight != 0.0
            or e.combined_fumble_luck_weight != 0.0
            for e in experiments
        ),
        turnover_stability_features,
        _REQUIRED_TURNOVER_STABILITY_COLUMNS,
        "Turnover-stability",
    )
    _validate_group(
        any(
            e.recent_off_epa_weight != 0.0
            or e.recent_def_epa_weight != 0.0
            or e.off_epa_trend_weight != 0.0
            or e.def_epa_trend_weight != 0.0
            or e.off_success_trend_weight != 0.0
            or e.def_success_trend_weight != 0.0
            for e in experiments
        ),
        recent_form_features,
        _REQUIRED_RECENT_FORM_COLUMNS,
        "Recent-form",
    )
    _validate_group(
        any(
            e.opponent_adjusted_off_epa_weight != 0.0
            or e.opponent_adjusted_def_epa_weight != 0.0
            or e.offensive_schedule_difficulty_weight != 0.0
            or e.defensive_schedule_difficulty_weight != 0.0
            for e in experiments
        ),
        opponent_adjusted_features,
        _REQUIRED_OPPONENT_ADJUSTED_COLUMNS,
        "Opponent-adjusted",
    )
    _validate_group(
        any(
            e.penalty_yards_discipline_weight != 0.0
            or e.penalty_rate_discipline_weight != 0.0
            or e.offensive_penalty_discipline_weight != 0.0
            or e.defensive_penalty_discipline_weight != 0.0
            for e in experiments
        ),
        penalty_discipline_features,
        _REQUIRED_PENALTY_DISCIPLINE_COLUMNS,
        "Penalty-discipline",
    )
    _validate_group(
        any(
            e.travel_miles_weight != 0.0
            or e.travel_time_zone_weight != 0.0
            for e in experiments
        ),
        travel_fatigue_features,
        _REQUIRED_TRAVEL_FATIGUE_COLUMNS,
        "Travel-fatigue",
    )
    _validate_group(
        any(
            e.adverse_weather_weight != 0.0
            or e.indoor_environment_weight != 0.0
            or e.high_wind_weight != 0.0
            or e.extreme_cold_weight != 0.0
            for e in experiments
        ),
        game_environment_features,
        _REQUIRED_GAME_ENVIRONMENT_COLUMNS,
        "Game-environment",
    )
    _validate_group(
        any(e.forecast_high_wind_weight != 0.0 for e in experiments),
        forecast_weather_features,
        _REQUIRED_FORECAST_WEATHER_COLUMNS,
        "Forecast-weather",
    )
    _validate_group(
        any(
            e.pace_play_volume_weight != 0.0
            or e.pace_seconds_weight != 0.0
            or e.tempo_index_weight != 0.0
            for e in experiments
        ),
        pace_tempo_features,
        _REQUIRED_PACE_TEMPO_COLUMNS,
        "Pace-tempo",
    )
    _validate_group(
        any(
            e.performance_stability_weight != 0.0
            or e.recent_margin_weight != 0.0
            or e.close_game_experience_weight != 0.0
            for e in experiments
        ),
        performance_stability_features,
        _REQUIRED_PERFORMANCE_STABILITY_COLUMNS,
        "Performance-stability",
    )
    _validate_group(
        any(
            e.first_half_off_epa_weight != 0.0
            or e.first_half_def_epa_weight != 0.0
            or e.first_half_play_volume_weight != 0.0
            for e in experiments
        ),
        first_half_form_features,
        _REQUIRED_FIRST_HALF_FORM_COLUMNS,
        "First-half-form",
    )
    _validate_group(
        any(
            e.explosive_pass_rate_weight != 0.0
            or e.explosive_rush_rate_weight != 0.0
            or e.explosive_play_rate_weight != 0.0
            for e in experiments
        ),
        explosive_play_features,
        _REQUIRED_EXPLOSIVE_PLAY_COLUMNS,
        "Explosive-play",
    )
    _validate_group(
        any(
            e.off_success_rate_weight != 0.0
            or e.def_success_prevention_weight != 0.0
            or e.success_rate_matchup_weight != 0.0
            or e.negative_play_matchup_weight != 0.0
            for e in experiments
        ),
        play_consistency_features,
        _REQUIRED_PLAY_CONSISTENCY_COLUMNS,
        "Play-consistency",
    )

    if (
        injury_features is not None
        and any(e.injury_weight != 0.0 for e in experiments)
        and not bool(injury_features["source_timestamp_available"].all())
    ):
        raise ValueError(
            "Injury experiments require timestamp-available features."
        )


def _validate_group(
    required_by_weight: bool,
    features: pl.DataFrame | None,
    required: frozenset[str],
    label: str,
) -> None:
    if required_by_weight and features is None:
        raise ValueError(
            f"{label} features are required for non-zero {label.lower()} weights."
        )
    if features is not None:
        _validate_frame(features, required, label)


def _validate_feature(
    experiments: list[ExperimentConfig],
    features: pl.DataFrame | None,
    required: frozenset[str],
    weight_attr: str,
    label: str,
) -> None:
    if (
        any(getattr(e, weight_attr) != 0.0 for e in experiments)
        and features is None
    ):
        raise ValueError(
            f"{label} features are required for non-zero {weight_attr}."
        )
    if features is not None:
        _validate_frame(features, required, label)


def _validate_frame(
    features: pl.DataFrame,
    required: frozenset[str],
    label: str,
) -> None:
    missing = required.difference(features.columns)
    if missing:
        raise ValueError(
            f"{label} features are missing columns: "
            + ", ".join(sorted(missing))
        )
    if features["game_id"].n_unique() != features.height:
        raise ValueError(
            f"{label} features contain duplicate game rows."
        )


def selection_score(
    *,
    winner_accuracy: float,
    brier_score: float,
    log_loss: float,
    margin_rmse: float,
) -> float:
    return (
        brier_score
        + 0.25 * log_loss
        + 0.01 * margin_rmse
        - 0.10 * winner_accuracy
    )



