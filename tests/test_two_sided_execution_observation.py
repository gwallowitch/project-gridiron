from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path

import pytest

from gridiron.market.moneyline import american_odds_to_implied_probability
from gridiron.market.operational_history import (
    OperationalHistoryError,
    build_operational_history_record,
    calculate_two_sided_execution_observation,
    canonical_json,
    read_operational_history,
)
from scripts.gridiron_operational_prediction import build_operational_prediction

BOOKS = ("BetMGM", "FanDuel", "DraftKings")


def snapshot() -> dict[str, object]:
    return {
        "schema_version": 1,
        "provider": "the-odds-api-operational",
        "captured_at": "2026-09-09T18:20:00Z",
        "game": {
            "game_id": "2026_01_NE_SEA",
            "season": 2026,
            "week": 1,
            "season_type": "REG",
            "home_team": "SEA",
            "away_team": "NE",
            "kickoff_at": "2026-09-10T00:20:00Z",
        },
        "offers": [
            {
                "book": book,
                "home_odds": -175 - index,
                "away_odds": 145 + index,
                "observed_at": "2026-09-09T18:19:00Z",
            }
            for index, book in enumerate(BOOKS)
        ],
    }


def rehash(record: dict[str, object]) -> dict[str, object]:
    material = deepcopy(record)
    material.pop("observation_id", None)
    material["observation_id"] = hashlib.sha256(
        canonical_json(material).encode("utf-8")
    ).hexdigest()
    return material


def write_record(path: Path, record: dict[str, object]) -> None:
    path.write_text(canonical_json(record) + "\n", encoding="utf-8")


def observation(
    *,
    home: float = 0.55,
    away: float = 0.45,
    home_odds: int = -200,
    away_odds: int = 150,
    selected: str = "HOME",
    is_bet: bool = False,
) -> dict[str, object]:
    return calculate_two_sided_execution_observation(
        model_home_probability=home,
        model_away_probability=away,
        draftkings_home_odds=home_odds,
        draftkings_away_odds=away_odds,
        frozen_selected_side=selected,
        frozen_is_bet=is_bet,
    )


def test_home_and_away_edges_use_their_independent_draftkings_prices() -> None:
    result = observation()
    assert result["home"]["edge"] == pytest.approx(
        0.55 - american_odds_to_implied_probability(-200)
    )
    assert result["away"]["edge"] == pytest.approx(
        0.45 - american_odds_to_implied_probability(150)
    )
    assert result["away"]["model_probability"] == pytest.approx(
        1.0 - result["home"]["model_probability"]
    )


def test_zero_edge_is_not_positive_and_exact_tie_is_neutral() -> None:
    result = observation(home=0.5, away=0.5, home_odds=100, away_odds=100)
    assert result["home"]["positive_edge"] is False
    assert result["away"]["positive_edge"] is False
    assert result["best_side"] == "TIE"
    assert result["best_edge"] == 0.0


def test_positive_home_and_away_edges_are_detected() -> None:
    home = observation(home=0.6, away=0.4, home_odds=-110, away_odds=-110)
    away = observation(home=0.4, away=0.6, home_odds=-110, away_odds=-110)
    assert home["home"]["positive_edge"] is True
    assert away["away"]["positive_edge"] is True


def test_no_bet_with_positive_opposite_edge_is_flagged() -> None:
    result = observation()
    assert result["opposite_side"] == "AWAY"
    assert result["opposite_side_positive"] is True
    assert result["missed_opposite_side_positive_edge"] is True
    assert result["best_side"] == "AWAY"


def test_frozen_bet_never_sets_missed_opposite_flag() -> None:
    result = observation(is_bet=True)
    assert result["opposite_side_positive"] is True
    assert result["missed_opposite_side_positive_edge"] is False


def test_opposite_side_tracks_frozen_selected_side() -> None:
    result = observation(selected="AWAY")
    assert result["opposite_side"] == "HOME"
    assert result["opposite_side_edge"] == result["home"]["edge"]


def test_both_positive_edges_are_retained_and_classified() -> None:
    result = observation(home=0.5, away=0.5, home_odds=120, away_odds=120)
    assert result["home"]["positive_edge"] is True
    assert result["away"]["positive_edge"] is True
    assert result["both_sides_positive"] is True
    assert result["best_side"] == "TIE"


def test_building_challenger_does_not_change_frozen_decision() -> None:
    prediction = build_operational_prediction(
        snapshot(), def_epa=0.0, def_epa_source="frozen Week 1 neutral rule"
    )
    frozen = {
        field: deepcopy(prediction[field])
        for field in ("selected_side", "selected_odds", "edge", "is_bet")
    }
    record = build_operational_history_record(prediction)
    assert {
        "selected_side": record["decision"]["selected_side"],
        "selected_odds": record["decision"]["execution_odds"],
        "edge": record["decision"]["edge"],
        "is_bet": record["decision"]["is_bet"],
    } == frozen
    assert {field: prediction[field] for field in frozen} == frozen


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("home", "edge"), 0.9),
        (("away", "edge"), 0.9),
        (("draftkings", "home_break_even_probability"), 0.9),
        (("best_side",), "INVALID"),
        (("opposite_side_positive",), "INVALID"),
        (("missed_opposite_side_positive_edge",), "INVALID"),
    ],
)
def test_self_hashed_challenger_tampering_is_rejected(
    tmp_path: Path, path: tuple[str, ...], value: object
) -> None:
    prediction = build_operational_prediction(
        snapshot(), def_epa=0.0, def_epa_source="frozen Week 1 neutral rule"
    )
    record = build_operational_history_record(prediction)
    target = record["two_sided_execution"]
    for field in path[:-1]:
        target = target[field]
    target[path[-1]] = value
    history = tmp_path / "history.jsonl"
    write_record(history, rehash(record))
    with pytest.raises(OperationalHistoryError, match="two_sided_execution"):
        read_operational_history(history)


def test_challenger_build_makes_no_extra_provider_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("challenger attempted network access")

    monkeypatch.setattr("urllib.request.urlopen", reject_network)
    prediction = build_operational_prediction(
        snapshot(), def_epa=0.0, def_epa_source="frozen Week 1 neutral rule"
    )
    record = build_operational_history_record(prediction)
    assert (
        record["two_sided_execution"]["identity"]
        == "two-sided-execution-observation-v1"
    )
