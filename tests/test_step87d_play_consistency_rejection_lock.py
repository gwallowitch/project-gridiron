from pathlib import Path

from gridiron.experiments.config import load_experiments


def experiments():
    return load_experiments(Path("config") / "experiments.toml")


def test_87d_has_single_locked_baseline() -> None:
    rows = experiments()
    assert len(rows) == 1
    assert rows[0].name == "six_weight_v1_locked"


def test_87d_preserves_promoted_six_weights() -> None:
    row = experiments()[0]

    assert row.rest_weight == 0.20
    assert row.off_sack_weight == 10.0
    assert row.punt_return_weight == 0.24
    assert row.long_field_avoidance_weight == 1.0
    assert row.def_epa_trend_weight == 5.25
    assert row.defensive_schedule_difficulty_weight == 2.25


def test_87d_parks_play_consistency_family() -> None:
    row = experiments()[0]

    assert row.off_success_rate_weight == 0.0
    assert row.def_success_prevention_weight == 0.0
    assert row.success_rate_matchup_weight == 0.0
    assert row.negative_play_matchup_weight == 0.0


def test_87d_keeps_recent_rejected_families_parked() -> None:
    row = experiments()[0]

    assert row.first_half_off_epa_weight == 0.0
    assert row.first_half_def_epa_weight == 0.0
    assert row.first_half_play_volume_weight == 0.0

    assert row.explosive_pass_rate_weight == 0.0
    assert row.explosive_rush_rate_weight == 0.0
    assert row.explosive_play_rate_weight == 0.0

    assert row.performance_stability_weight == 0.0
    assert row.recent_margin_weight == 0.0
    assert row.close_game_experience_weight == 0.0
