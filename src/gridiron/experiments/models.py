"""Data models for Project Gridiron experiments."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    name: str
    home_field_advantage: float
    probability_scale: float
    margin_scale: float = 1.0
    margin_intercept: float = 0.0
    rest_weight: float = 0.0
    qb_weight: float = 0.0
    injury_weight: float = 0.0
    early_down_off_weight: float = 0.0
    early_down_def_weight: float = 0.0
    early_down_success_weight: float = 0.0
    turnover_int_weight: float = 0.0
    turnover_fumble_weight: float = 0.0
    pass_off_epa_weight: float = 0.0
    pass_def_epa_weight: float = 0.0
    pass_success_weight: float = 0.0
    off_sack_weight: float = 0.0
    def_sack_weight: float = 0.0
    explosive_pass_weight: float = 0.0
    red_zone_off_epa_weight: float = 0.0
    red_zone_def_epa_weight: float = 0.0
    red_zone_success_weight: float = 0.0
    red_zone_td_rate_weight: float = 0.0
    rush_off_epa_weight: float = 0.0
    rush_def_epa_weight: float = 0.0
    rush_success_weight: float = 0.0
    explosive_run_weight: float = 0.0
    drive_off_epa_weight: float = 0.0
    drive_def_epa_weight: float = 0.0
    scoring_drive_rate_weight: float = 0.0
    td_drive_rate_weight: float = 0.0
    plays_per_drive_weight: float = 0.0
    fg_make_rate_weight: float = 0.0
    punt_coverage_weight: float = 0.0
    punt_return_weight: float = 0.0
    punt_touchback_weight: float = 0.0
    third_down_off_epa_weight: float = 0.0
    third_down_def_epa_weight: float = 0.0
    third_down_conversion_weight: float = 0.0
    third_down_stop_weight: float = 0.0
    third_and_long_weight: float = 0.0
    pass_protection_weight: float = 0.0
    pressure_creation_weight: float = 0.0
    clean_dropback_weight: float = 0.0
    pressured_off_epa_weight: float = 0.0
    pressured_def_epa_weight: float = 0.0
    neutral_off_epa_weight: float = 0.0
    neutral_def_epa_weight: float = 0.0
    neutral_success_weight: float = 0.0
    neutral_yards_per_play_weight: float = 0.0
    neutral_explosive_weight: float = 0.0
    off_start_field_position_weight: float = 0.0
    def_field_position_weight: float = 0.0
    short_field_rate_weight: float = 0.0
    long_field_avoidance_weight: float = 0.0
    hidden_yards_field_position_weight: float = 0.0
    fourth_down_off_epa_weight: float = 0.0
    fourth_down_def_epa_weight: float = 0.0
    fourth_down_conversion_weight: float = 0.0
    fourth_down_stop_weight: float = 0.0
    fourth_short_conversion_weight: float = 0.0
    explosive_off_rate_weight: float = 0.0
    explosive_suppression_weight: float = 0.0
    chunk_off_rate_weight: float = 0.0
    chunk_suppression_weight: float = 0.0
    explosive_yards_share_weight: float = 0.0
    turnover_protection_weight: float = 0.0
    takeaway_creation_weight: float = 0.0
    interception_protection_weight: float = 0.0
    interception_creation_weight: float = 0.0
    off_fumble_luck_weight: float = 0.0
    def_fumble_luck_weight: float = 0.0
    combined_fumble_luck_weight: float = 0.0
    recent_off_epa_weight: float = 0.0
    recent_def_epa_weight: float = 0.0
    off_epa_trend_weight: float = 0.0
    def_epa_trend_weight: float = 0.0
    off_success_trend_weight: float = 0.0
    def_success_trend_weight: float = 0.0
    opponent_adjusted_off_epa_weight: float = 0.0
    opponent_adjusted_def_epa_weight: float = 0.0
    offensive_schedule_difficulty_weight: float = 0.0
    defensive_schedule_difficulty_weight: float = 0.0
    travel_miles_weight: float = 0.0
    travel_time_zone_weight: float = 0.0
    adverse_weather_weight: float = 0.0
    indoor_environment_weight: float = 0.0
    high_wind_weight: float = 0.0
    extreme_cold_weight: float = 0.0
    forecast_high_wind_weight: float = 0.0
    pace_play_volume_weight: float = 0.0
    pace_seconds_weight: float = 0.0
    tempo_index_weight: float = 0.0
    performance_stability_weight: float = 0.0
    recent_margin_weight: float = 0.0
    close_game_experience_weight: float = 0.0
    first_half_off_epa_weight: float = 0.0
    first_half_def_epa_weight: float = 0.0
    first_half_play_volume_weight: float = 0.0
    explosive_pass_rate_weight: float = 0.0
    explosive_rush_rate_weight: float = 0.0
    explosive_play_rate_weight: float = 0.0
    off_success_rate_weight: float = 0.0
    def_success_prevention_weight: float = 0.0
    success_rate_matchup_weight: float = 0.0
    negative_play_matchup_weight: float = 0.0
    penalty_yards_discipline_weight: float = 0.0
    penalty_rate_discipline_weight: float = 0.0
    offensive_penalty_discipline_weight: float = 0.0
    defensive_penalty_discipline_weight: float = 0.0


@dataclass(frozen=True, slots=True)
class ExperimentResult:
    name: str
    season: int
    home_field_advantage: float
    probability_scale: float
    margin_scale: float
    margin_intercept: float
    rest_weight: float
    qb_weight: float
    injury_weight: float
    early_down_off_weight: float
    early_down_def_weight: float
    early_down_success_weight: float
    turnover_int_weight: float
    turnover_fumble_weight: float
    pass_off_epa_weight: float
    pass_def_epa_weight: float
    pass_success_weight: float
    off_sack_weight: float
    def_sack_weight: float
    explosive_pass_weight: float
    red_zone_off_epa_weight: float
    red_zone_def_epa_weight: float
    red_zone_success_weight: float
    red_zone_td_rate_weight: float
    rush_off_epa_weight: float
    rush_def_epa_weight: float
    rush_success_weight: float
    explosive_run_weight: float
    drive_off_epa_weight: float
    drive_def_epa_weight: float
    scoring_drive_rate_weight: float
    td_drive_rate_weight: float
    plays_per_drive_weight: float
    fg_make_rate_weight: float
    punt_coverage_weight: float
    punt_return_weight: float
    punt_touchback_weight: float
    third_down_off_epa_weight: float
    third_down_def_epa_weight: float
    third_down_conversion_weight: float
    third_down_stop_weight: float
    third_and_long_weight: float
    pass_protection_weight: float
    pressure_creation_weight: float
    clean_dropback_weight: float
    pressured_off_epa_weight: float
    pressured_def_epa_weight: float
    neutral_off_epa_weight: float
    neutral_def_epa_weight: float
    neutral_success_weight: float
    neutral_yards_per_play_weight: float
    neutral_explosive_weight: float
    off_start_field_position_weight: float
    def_field_position_weight: float
    short_field_rate_weight: float
    long_field_avoidance_weight: float
    hidden_yards_field_position_weight: float
    fourth_down_off_epa_weight: float
    fourth_down_def_epa_weight: float
    fourth_down_conversion_weight: float
    fourth_down_stop_weight: float
    fourth_short_conversion_weight: float
    explosive_off_rate_weight: float
    explosive_suppression_weight: float
    chunk_off_rate_weight: float
    chunk_suppression_weight: float
    explosive_yards_share_weight: float
    turnover_protection_weight: float
    takeaway_creation_weight: float
    interception_protection_weight: float
    interception_creation_weight: float
    off_fumble_luck_weight: float
    def_fumble_luck_weight: float
    combined_fumble_luck_weight: float
    recent_off_epa_weight: float
    recent_def_epa_weight: float
    off_epa_trend_weight: float
    def_epa_trend_weight: float
    off_success_trend_weight: float
    def_success_trend_weight: float
    opponent_adjusted_off_epa_weight: float
    opponent_adjusted_def_epa_weight: float
    offensive_schedule_difficulty_weight: float
    defensive_schedule_difficulty_weight: float
    travel_miles_weight: float
    travel_time_zone_weight: float
    adverse_weather_weight: float
    indoor_environment_weight: float
    high_wind_weight: float
    extreme_cold_weight: float
    forecast_high_wind_weight: float
    pace_play_volume_weight: float
    pace_seconds_weight: float
    tempo_index_weight: float
    performance_stability_weight: float
    recent_margin_weight: float
    close_game_experience_weight: float
    first_half_off_epa_weight: float
    first_half_def_epa_weight: float
    first_half_play_volume_weight: float
    explosive_pass_rate_weight: float
    explosive_rush_rate_weight: float
    explosive_play_rate_weight: float
    off_success_rate_weight: float
    def_success_prevention_weight: float
    success_rate_matchup_weight: float
    negative_play_matchup_weight: float
    penalty_yards_discipline_weight: float
    penalty_rate_discipline_weight: float
    offensive_penalty_discipline_weight: float
    defensive_penalty_discipline_weight: float
    games_evaluated: int
    winner_accuracy: float
    brier_score: float
    log_loss: float
    margin_mae: float
    margin_rmse: float
    selection_score: float
    generated_at: str

    @classmethod
    def create(
        cls,
        *,
        config: ExperimentConfig,
        season: int,
        games_evaluated: int,
        winner_accuracy: float,
        brier_score: float,
        log_loss: float,
        margin_mae: float,
        margin_rmse: float,
        selection_score: float,
    ) -> ExperimentResult:
        return cls(
            **asdict(config),
            season=season,
            games_evaluated=games_evaluated,
            winner_accuracy=winner_accuracy,
            brier_score=brier_score,
            log_loss=log_loss,
            margin_mae=margin_mae,
            margin_rmse=margin_rmse,
            selection_score=selection_score,
            generated_at=datetime.now(UTC).isoformat(),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


