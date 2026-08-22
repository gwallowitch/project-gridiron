"""Multi-season research orchestration."""
from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import polars as pl

from gridiron.core.paths import ProjectPaths
from gridiron.experiments.models import ExperimentConfig
from gridiron.experiments.runner import run_experiments
from gridiron.research.models import ResearchRun, SeasonResearchResult


def run_research(
    *,
    profile: str,
    seasons: tuple[int, ...],
    experiments: list[ExperimentConfig],
    project_root: Path | str = Path("."),
) -> ResearchRun:
    if not seasons:
        raise ValueError("Research requires at least one season.")
    if not experiments:
        raise ValueError("Research requires at least one experiment.")

    started = perf_counter()
    paths = ProjectPaths.from_root(project_root)
    results = []

    needs_qb = any(e.qb_weight != 0.0 for e in experiments)
    needs_injury = any(e.injury_weight != 0.0 for e in experiments)
    needs_early_down = any(
        e.early_down_off_weight != 0.0
        or e.early_down_def_weight != 0.0
        or e.early_down_success_weight != 0.0
        for e in experiments
    )
    needs_turnovers = any(
        e.turnover_int_weight != 0.0
        or e.turnover_fumble_weight != 0.0
        for e in experiments
    )
    needs_passing = any(
        e.pass_off_epa_weight != 0.0
        or e.pass_def_epa_weight != 0.0
        or e.pass_success_weight != 0.0
        or e.off_sack_weight != 0.0
        or e.def_sack_weight != 0.0
        or e.explosive_pass_weight != 0.0
        for e in experiments
    )
    needs_red_zone = any(
        e.red_zone_off_epa_weight != 0.0
        or e.red_zone_def_epa_weight != 0.0
        or e.red_zone_success_weight != 0.0
        or e.red_zone_td_rate_weight != 0.0
        for e in experiments
    )
    needs_rushing = any(
        e.rush_off_epa_weight != 0.0
        or e.rush_def_epa_weight != 0.0
        or e.rush_success_weight != 0.0
        or e.explosive_run_weight != 0.0
        for e in experiments
    )
    needs_drive = any(
        e.drive_off_epa_weight != 0.0
        or e.drive_def_epa_weight != 0.0
        or e.scoring_drive_rate_weight != 0.0
        or e.td_drive_rate_weight != 0.0
        or e.plays_per_drive_weight != 0.0
        for e in experiments
    )
    needs_special_teams = any(
        e.fg_make_rate_weight != 0.0
        or e.punt_coverage_weight != 0.0
        or e.punt_return_weight != 0.0
        or e.punt_touchback_weight != 0.0
        for e in experiments
    )
    needs_third_down = any(
        e.third_down_off_epa_weight != 0.0
        or e.third_down_def_epa_weight != 0.0
        or e.third_down_conversion_weight != 0.0
        or e.third_down_stop_weight != 0.0
        or e.third_and_long_weight != 0.0
        for e in experiments
    )
    needs_pressure = any(
        e.pass_protection_weight != 0.0
        or e.pressure_creation_weight != 0.0
        or e.clean_dropback_weight != 0.0
        or e.pressured_off_epa_weight != 0.0
        or e.pressured_def_epa_weight != 0.0
        for e in experiments
    )
    needs_neutral_state = any(
        e.neutral_off_epa_weight != 0.0
        or e.neutral_def_epa_weight != 0.0
        or e.neutral_success_weight != 0.0
        or e.neutral_yards_per_play_weight != 0.0
        or e.neutral_explosive_weight != 0.0
        for e in experiments
    )
    needs_field_position = any(
        e.off_start_field_position_weight != 0.0
        or e.def_field_position_weight != 0.0
        or e.short_field_rate_weight != 0.0
        or e.long_field_avoidance_weight != 0.0
        or e.hidden_yards_field_position_weight != 0.0
        for e in experiments
    )
    needs_fourth_down = any(
        e.fourth_down_off_epa_weight != 0.0
        or e.fourth_down_def_epa_weight != 0.0
        or e.fourth_down_conversion_weight != 0.0
        or e.fourth_down_stop_weight != 0.0
        or e.fourth_short_conversion_weight != 0.0
        for e in experiments
    )
    needs_explosive_suppression = any(
        e.explosive_off_rate_weight != 0.0
        or e.explosive_suppression_weight != 0.0
        or e.chunk_off_rate_weight != 0.0
        or e.chunk_suppression_weight != 0.0
        or e.explosive_yards_share_weight != 0.0
        for e in experiments
    )
    needs_turnover_stability = any(
        e.turnover_protection_weight != 0.0
        or e.takeaway_creation_weight != 0.0
        or e.interception_protection_weight != 0.0
        or e.interception_creation_weight != 0.0
        or e.off_fumble_luck_weight != 0.0
        or e.def_fumble_luck_weight != 0.0
        or e.combined_fumble_luck_weight != 0.0
        for e in experiments
    )
    needs_recent_form = any(
        e.recent_off_epa_weight != 0.0
        or e.recent_def_epa_weight != 0.0
        or e.off_epa_trend_weight != 0.0
        or e.def_epa_trend_weight != 0.0
        or e.off_success_trend_weight != 0.0
        or e.def_success_trend_weight != 0.0
        for e in experiments
    )
    needs_opponent_adjusted = any(
        e.opponent_adjusted_off_epa_weight != 0.0
        or e.opponent_adjusted_def_epa_weight != 0.0
        or e.offensive_schedule_difficulty_weight != 0.0
        or e.defensive_schedule_difficulty_weight != 0.0
        for e in experiments
    )
    needs_penalty_discipline = any(
        e.penalty_yards_discipline_weight != 0.0
        or e.penalty_rate_discipline_weight != 0.0
        or e.offensive_penalty_discipline_weight != 0.0
        or e.defensive_penalty_discipline_weight != 0.0
        for e in experiments
    )
    needs_travel_fatigue = any(
        e.travel_miles_weight != 0.0
        or e.travel_time_zone_weight != 0.0
        for e in experiments
    )
    needs_game_environment = any(
        e.adverse_weather_weight != 0.0
        or e.indoor_environment_weight != 0.0
        or e.high_wind_weight != 0.0
        or e.extreme_cold_weight != 0.0
        for e in experiments
    )
    needs_forecast_weather = any(
        e.forecast_high_wind_weight != 0.0
        for e in experiments
    )
    needs_pace_tempo = any(
        e.pace_play_volume_weight != 0.0
        or e.pace_seconds_weight != 0.0
        or e.tempo_index_weight != 0.0
        for e in experiments
    )
    needs_performance_stability = any(
        e.performance_stability_weight != 0.0
        or e.recent_margin_weight != 0.0
        or e.close_game_experience_weight != 0.0
        for e in experiments
    )
    needs_first_half_form = any(
        e.first_half_off_epa_weight != 0.0
        or e.first_half_def_epa_weight != 0.0
        or e.first_half_play_volume_weight != 0.0
        for e in experiments
    )
    needs_explosive_play = any(
        e.explosive_pass_rate_weight != 0.0
        or e.explosive_rush_rate_weight != 0.0
        or e.explosive_play_rate_weight != 0.0
        for e in experiments
    )
    needs_play_consistency = any(
        e.off_success_rate_weight != 0.0
        or e.def_success_prevention_weight != 0.0
        or e.success_rate_matchup_weight != 0.0
        or e.negative_play_matchup_weight != 0.0
        for e in experiments
    )

    for season in seasons:
        schedule_path = paths.schedule_file(season)
        pgr_path = paths.pgr_file(season)
        rest_path = paths.rest_features_file(season)
        qb_path = paths.qb_features_file(season)
        injury_path = paths.injury_features_file(season)
        early_down_path = paths.early_down_features_file(season)
        turnover_path = paths.root / "data" / "curated" / "turnover_features" / f"turnover_features_{season}.parquet"
        passing_path = paths.root / "data" / "curated" / "passing_features" / f"passing_features_{season}.parquet"
        red_zone_path = paths.root / "data" / "curated" / "red_zone_features" / f"red_zone_features_{season}.parquet"
        rushing_path = paths.root / "data" / "curated" / "rushing_features" / f"rushing_features_{season}.parquet"
        drive_path = paths.root / "data" / "curated" / "drive_efficiency_features" / f"drive_efficiency_features_{season}.parquet"
        special_teams_path = paths.root / "data" / "curated" / "special_teams_features" / f"special_teams_features_{season}.parquet"
        third_down_path = paths.root / "data" / "curated" / "third_down_features" / f"third_down_features_{season}.parquet"
        pressure_path = paths.root / "data" / "curated" / "pressure_features" / f"pressure_features_{season}.parquet"
        neutral_state_path = paths.root / "data" / "curated" / "neutral_state_features" / f"neutral_state_features_{season}.parquet"
        field_position_path = paths.root / "data" / "curated" / "field_position_features" / f"field_position_features_{season}.parquet"
        fourth_down_path = paths.root / "data" / "curated" / "fourth_down_features" / f"fourth_down_features_{season}.parquet"
        explosive_suppression_path = paths.root / "data" / "curated" / "explosive_suppression_features" / f"explosive_suppression_features_{season}.parquet"
        turnover_stability_path = paths.root / "data" / "curated" / "turnover_stability_features" / f"turnover_stability_features_{season}.parquet"
        recent_form_path = paths.root / "data" / "curated" / "recent_form_features" / f"recent_form_features_{season}.parquet"
        opponent_adjusted_path = paths.root / "data" / "curated" / "opponent_adjusted_features" / f"opponent_adjusted_features_{season}.parquet"
        penalty_discipline_path = paths.root / "data" / "curated" / "penalty_discipline_features" / f"penalty_discipline_features_{season}.parquet"
        travel_fatigue_path = paths.root / "data" / "curated" / "travel_fatigue_features" / f"travel_fatigue_features_{season}.parquet"
        game_environment_path = paths.root / "data" / "curated" / "game_environment_features" / f"game_environment_features_{season}.parquet"
        forecast_weather_path = paths.root / "data" / "curated" / "open_meteo_research_forecasts" / f"open_meteo_research_forecasts_{season}.parquet"
        pace_tempo_path = paths.root / "data" / "curated" / "pace_tempo_features" / f"pace_tempo_features_{season}.parquet"
        performance_stability_path = paths.root / "data" / "curated" / "performance_stability_features" / f"performance_stability_features_{season}.parquet"
        first_half_form_path = paths.root / "data" / "curated" / "first_half_form_features" / f"first_half_form_features_{season}.parquet"
        explosive_play_path = paths.root / "data" / "curated" / "explosive_play_features" / f"explosive_play_features_{season}.parquet"
        play_consistency_path = paths.root / "data" / "curated" / "play_consistency_features" / f"play_consistency_features_{season}.parquet"

        required = [schedule_path, pgr_path, rest_path]
        if needs_qb:
            required.append(qb_path)
        if needs_injury:
            required.append(injury_path)
        if needs_early_down:
            required.append(early_down_path)
        if needs_turnovers:
            required.append(turnover_path)
        if needs_passing:
            required.append(passing_path)
        if needs_red_zone:
            required.append(red_zone_path)
        if needs_rushing:
            required.append(rushing_path)
        if needs_drive:
            required.append(drive_path)
        if needs_special_teams:
            required.append(special_teams_path)
        if needs_third_down:
            required.append(third_down_path)
        if needs_pressure:
            required.append(pressure_path)
        if needs_neutral_state:
            required.append(neutral_state_path)
        if needs_field_position:
            required.append(field_position_path)
        if needs_fourth_down:
            required.append(fourth_down_path)
        if needs_explosive_suppression:
            required.append(explosive_suppression_path)
        if needs_turnover_stability:
            required.append(turnover_stability_path)
        if needs_recent_form:
            required.append(recent_form_path)
        if needs_opponent_adjusted:
            required.append(opponent_adjusted_path)
        if needs_penalty_discipline:
            required.append(penalty_discipline_path)
        if needs_travel_fatigue:
            required.append(travel_fatigue_path)
        if needs_game_environment:
            required.append(game_environment_path)
        if needs_forecast_weather:
            required.append(forecast_weather_path)
        if needs_pace_tempo:
            required.append(pace_tempo_path)
        if needs_performance_stability:
            required.append(performance_stability_path)
        if needs_first_half_form:
            required.append(first_half_form_path)
        if needs_explosive_play:
            required.append(explosive_play_path)
        if needs_play_consistency:
            required.append(play_consistency_path)

        missing = [path for path in required if not path.exists()]
        if missing:
            raise FileNotFoundError(
                f"Research inputs are missing for season {season}: "
                + ", ".join(str(path) for path in missing)
            )

        season_results = run_experiments(
            pl.read_parquet(schedule_path),
            pl.read_parquet(pgr_path),
            experiments,
            rest_features=pl.read_parquet(rest_path),
            qb_features=pl.read_parquet(qb_path) if qb_path.exists() else None,
            injury_features=pl.read_parquet(injury_path) if injury_path.exists() else None,
            early_down_features=pl.read_parquet(early_down_path) if early_down_path.exists() else None,
            turnover_features=pl.read_parquet(turnover_path) if turnover_path.exists() else None,
            passing_features=pl.read_parquet(passing_path) if passing_path.exists() else None,
            red_zone_features=pl.read_parquet(red_zone_path) if red_zone_path.exists() else None,
            rushing_features=pl.read_parquet(rushing_path) if rushing_path.exists() else None,
            drive_efficiency_features=pl.read_parquet(drive_path) if drive_path.exists() else None,
            special_teams_features=pl.read_parquet(special_teams_path) if special_teams_path.exists() else None,
            third_down_features=pl.read_parquet(third_down_path) if third_down_path.exists() else None,
            pressure_features=pl.read_parquet(pressure_path) if pressure_path.exists() else None,
            neutral_state_features=pl.read_parquet(neutral_state_path) if neutral_state_path.exists() else None,
            field_position_features=pl.read_parquet(field_position_path) if field_position_path.exists() else None,
            fourth_down_features=pl.read_parquet(fourth_down_path) if fourth_down_path.exists() else None,
            explosive_suppression_features=pl.read_parquet(explosive_suppression_path) if explosive_suppression_path.exists() else None,
            turnover_stability_features=pl.read_parquet(turnover_stability_path) if turnover_stability_path.exists() else None,
            recent_form_features=pl.read_parquet(recent_form_path) if recent_form_path.exists() else None,
            opponent_adjusted_features=pl.read_parquet(opponent_adjusted_path) if opponent_adjusted_path.exists() else None,
            penalty_discipline_features=pl.read_parquet(penalty_discipline_path) if penalty_discipline_path.exists() else None,
            travel_fatigue_features=pl.read_parquet(travel_fatigue_path) if travel_fatigue_path.exists() else None,
            game_environment_features=pl.read_parquet(game_environment_path) if game_environment_path.exists() else None,
            forecast_weather_features=pl.read_parquet(forecast_weather_path) if forecast_weather_path.exists() else None,
            pace_tempo_features=pl.read_parquet(pace_tempo_path) if pace_tempo_path.exists() else None,
            performance_stability_features=pl.read_parquet(performance_stability_path) if performance_stability_path.exists() else None,
            first_half_form_features=pl.read_parquet(first_half_form_path) if first_half_form_path.exists() else None,
            explosive_play_features=pl.read_parquet(explosive_play_path) if explosive_play_path.exists() else None,
            play_consistency_features=pl.read_parquet(play_consistency_path) if play_consistency_path.exists() else None,
        )

        results.append(
            SeasonResearchResult(
                season=season,
                experiments=tuple(season_results),
            )
        )

    return ResearchRun(
        profile=profile,
        seasons=seasons,
        experiment_count=len(experiments),
        total_runs=len(seasons) * len(experiments),
        runtime_seconds=perf_counter() - started,
        generated_at=datetime.now(UTC).isoformat(),
        git_commit=_git_commit(paths.root),
        python_version=sys.version.split()[0],
        results=tuple(results),
    )


def _git_commit(project_root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip() or None
