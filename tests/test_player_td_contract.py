from __future__ import annotations

import inspect
from dataclasses import replace

import pytest

from gridiron.market.player_td_contract import (
    MARKET_KEY,
    ATTDObservation,
    FeatureAuthority,
    FeatureEvidence,
    FootballTDOutcome,
    ParticipationState,
    PersonnelAuthority,
    PersonnelEvidence,
    PlayerPrice,
    PlayerTDContractError,
    PriceState,
    RuleAuthority,
    SettlementResult,
    SettlementRule,
    TouchdownType,
    board_diagnostic,
    build_raw_artifact_metadata,
    cross_book_diagnostic,
    normalize_bookmaker,
    raw_price_break_even,
    settle_attd,
    validate_american_price,
)
from gridiron.market.player_td_identity import (
    PlayerResolution,
    ResolutionStatus,
    normalize_player_name,
    resolve_exact_name_team,
)
from gridiron.market.player_td_sample import (
    BOOKS,
    MAX_REQUEST_COUNT,
    PURPOSE,
    PlayerTDSampleError,
    SampleReadiness,
    build_sample_manifest,
)


def player(name="Jane Runner", yes=150, no=None, **kwargs):
    return PlayerPrice(name, yes, no, **kwargs)


def observation(**changes):
    base = {
        "provider": "the-odds-api", "provider_event_id": "event-1",
        "canonical_game_id": "2024_01_AAA_BBB", "season": 2024,
        "season_type": "REG", "week": 1, "home_team": "BBB",
        "away_team": "AAA", "kickoff_at": "2024-09-06T00:20:00Z",
        "requested_snapshot_at": "2024-09-05T23:20:00Z",
        "provider_snapshot_at": "2024-09-05T23:19:59Z",
        "bookmaker_key": "draftkings",
        "bookmaker_last_update": "2024-09-05T23:19:00Z",
        "raw_artifact_sha256": "a" * 64, "source_manifest_id": "sample-1",
        "acquisition_at": "2026-09-22T12:00:00Z", "players": (player(),),
    }
    return ATTDObservation(**(base | changes))


@pytest.mark.parametrize("price", [100, 250, -100, -325])
def test_valid_american_prices_and_raw_break_even(price):
    assert validate_american_price(price) == price
    assert 0 < raw_price_break_even(price) < 1


@pytest.mark.parametrize("price", [0, 1, 99, -1, -99, 100.0, float("nan"), "100"])
def test_invalid_american_prices_rejected(price):
    with pytest.raises(PlayerTDContractError):
        validate_american_price(price)


def test_exact_market_accepted_and_alternates_rejected():
    assert observation().provider_market_key == MARKET_KEY
    for wrong in ("player_1st_td", "player_tds", "player_tds_over"):
        with pytest.raises(PlayerTDContractError, match="wrong or alternate"):
            observation(provider_market_key=wrong)


def test_yes_no_states_are_independent():
    assert player(yes=150).price_state == PriceState.YES_ONLY
    assert player(yes=None, no=-200).price_state == PriceState.NO_ONLY
    assert player(yes=150, no=-200).price_state == PriceState.YES_AND_NO
    assert player(yes=None, no=None).price_state == PriceState.NO_VALID_PRICE
    assert player(duplicate_outcomes=True).price_state == PriceState.AMBIGUOUS_DUPLICATE


def test_event_identity_and_timestamp_mismatches_fail_closed():
    with pytest.raises(PlayerTDContractError, match="teams"):
        observation(home_team="AAA")
    with pytest.raises(PlayerTDContractError, match="canonical event"):
        observation(canonical_game_id="2024_01_OTHER_BBB")
    with pytest.raises(PlayerTDContractError, match="timestamps"):
        observation(provider_snapshot_at="2024-09-05T23:20:01Z")


def test_book_mapping_is_exact_and_unknown_is_rejected():
    assert [normalize_bookmaker(key) for key in BOOKS] == ["DraftKings", "FanDuel", "BetMGM"]
    assert normalize_bookmaker("draft-kings") is None
    with pytest.raises(PlayerTDContractError, match="unknown bookmaker"):
        observation(bookmaker_key="other")


def test_board_states_counts_and_no_arbitrary_completeness():
    prices = (player("A", 120, -160), player("B", 180, None))
    report = board_diagnostic(prices)
    assert report | {} == report
    assert report["status"] == "COMPLETE_UNVERIFIED"
    assert report["structurally_valid"] is True
    assert report["provider_board_completeness_verified"] is False
    assert report["player_count"] == 2 and report["both_count"] == 1
    assert board_diagnostic(())["status"] == "EMPTY"
    assert board_diagnostic((), book_present=False)["status"] == "BOOK_MISSING"
    assert board_diagnostic((), market_present=False)["status"] == "MARKET_MISSING"
    assert board_diagnostic(prices, multiple_markets=True)["status"] == "AMBIGUOUS"


def test_duplicate_player_and_duplicate_outcome_are_ambiguous():
    prices = (player("A"), player("A", 200))
    assert board_diagnostic(prices)["duplicate_names"] == ["a"]
    with pytest.raises(PlayerTDContractError, match="duplicate player"):
        observation(players=prices)
    assert board_diagnostic((player(duplicate_outcomes=True),))["status"] == "AMBIGUOUS"


def test_cross_book_union_intersection_are_deterministic():
    result = cross_book_diagnostic({
        "draftkings": (player("A"), player("B")),
        "fanduel": (player("B"), player("C")),
    })
    assert result["union"] == ["a", "b", "c"]
    assert result["intersection"] == ["b"]
    assert result["unique_by_book"] == {"draftkings": ["a"], "fanduel": ["c"]}


def test_name_suffix_and_exact_team_resolution():
    assert normalize_player_name("John Doe Jr.") == ("john doe", "jr")
    roster = ({"name": "John Doe Jr", "team": "AAA", "gsis_id": "00-1"},)
    result = resolve_exact_name_team("John Doe, Jr.", "AAA", roster,
                                     provider_event_id="e", bookmaker="DraftKings")
    assert result.status == ResolutionStatus.EXACT_NAME_TEAM
    assert result.selected_gsis_id == "00-1" and result.authoritative


def test_identity_ambiguity_conflict_and_unresolved_fail_closed():
    roster = (
        {"name": "Alex Smith", "team": "AAA", "gsis_id": "1"},
        {"name": "Alex Smith", "team": "BBB", "gsis_id": "2"},
    )
    ambiguous = resolve_exact_name_team("Alex Smith", None, roster,
                                        provider_event_id="e", bookmaker="FanDuel")
    assert ambiguous.status == ResolutionStatus.AMBIGUOUS and not ambiguous.authoritative
    unresolved = resolve_exact_name_team("Nobody", "AAA", roster,
                                         provider_event_id="e", bookmaker="FanDuel")
    assert unresolved.status == ResolutionStatus.UNRESOLVED
    with pytest.raises(ValueError):
        replace(ambiguous, selected_gsis_id="1")


def test_fuzzy_candidate_cannot_be_authority_and_manual_requires_provenance():
    unresolved = PlayerResolution("Jon Do", "jon do", None, "e", "BetMGM", "AAA",
                                  ("1",), None, ResolutionStatus.UNRESOLVED,
                                  "fuzzy candidate only")
    assert not unresolved.authoritative
    with pytest.raises(ValueError, match="review provenance"):
        replace(unresolved, status=ResolutionStatus.MANUAL_REVIEWED,
                selected_gsis_id="1")
    reviewed = replace(unresolved, status=ResolutionStatus.MANUAL_REVIEWED,
                       selected_gsis_id="1", manual_reviewer="reviewer",
                       manual_reviewed_at="2026-09-22T12:00:00Z")
    assert reviewed.authoritative and reviewed.provenance == "fuzzy candidate only"


def rule(authority=RuleAuthority.VERIFIED_CURRENT):
    return SettlementRule(
        "DraftKings", "NJ", "2025-12-22", "2025-12-22", None,
        "one play", "INCLUDED", frozenset({TouchdownType.RUSHING, TouchdownType.RECEIVING}),
        "VOID", "VOID", "LOSS", "RULE_SPECIFIC", "RULE_SPECIFIC",
        "official corrections", "https://example.invalid/rule", "2026-09-22",
        authority,
    )


def td(kind):
    return FootballTDOutcome("nflverse", "v1", "b" * 64, "game", "gsis", kind,
                             "play", 1, False, "2024-09-06T01:00:00Z", "original")


def test_settlement_separates_taxonomy_participation_and_rule_authority():
    assert settle_attd(rule=rule(), player_resolved=True, event_resolved=True,
                       participation=ParticipationState.PARTICIPATED,
                       touchdowns=(td(TouchdownType.RUSHING),)) == SettlementResult.WIN
    assert settle_attd(rule=rule(), player_resolved=True, event_resolved=True,
                       participation=ParticipationState.PARTICIPATED,
                       touchdowns=(td(TouchdownType.RECEIVING),)) == SettlementResult.WIN
    assert settle_attd(rule=rule(), player_resolved=True, event_resolved=True,
                       participation=ParticipationState.PARTICIPATED,
                       touchdowns=(td(TouchdownType.INTERCEPTION_RETURN),)) == SettlementResult.LOSS
    assert settle_attd(rule=rule(RuleAuthority.UNKNOWN), player_resolved=True,
                       event_resolved=True, participation=ParticipationState.PARTICIPATED,
                       touchdowns=()) == SettlementResult.UNRESOLVED
    assert settle_attd(rule=rule(), player_resolved=True, event_resolved=True,
                       participation=ParticipationState.INACTIVE,
                       touchdowns=()) == SettlementResult.VOID


def test_all_touchdown_and_participation_states_are_explicit():
    assert TouchdownType.KICKOFF_RETURN != TouchdownType.PUNT_RETURN
    assert TouchdownType.FUMBLE_RECOVERY_OFFENSE != TouchdownType.FUMBLE_RECOVERY_DEFENSE
    assert TouchdownType.INTERCEPTION_RETURN != TouchdownType.OTHER_DEFENSIVE_RETURN
    assert set(ParticipationState) == {
        ParticipationState.INACTIVE, ParticipationState.ACTIVE_NO_PLAY,
        ParticipationState.PARTICIPATED, ParticipationState.PARTICIPATION_UNKNOWN,
    }


def test_outcome_correction_provenance_is_preserved():
    original = td(TouchdownType.RUSHING)
    corrected = replace(original, correction_version="corrected-v2",
                        correction_timestamp="2024-09-07T00:00:00Z",
                        predecessor_artifact_sha256=original.source_artifact_sha256,
                        source_artifact_sha256="c" * 64)
    assert corrected.predecessor_artifact_sha256 == "b" * 64
    assert corrected.source_artifact_sha256 == "c" * 64


def test_feature_timing_allows_prior_available_and_rejects_leakage():
    valid = FeatureEvidence("prior carries", "2024-09-01T20:00:00Z",
                            "2024-09-05T23:00:00Z", "2024-09-06T00:20:00Z",
                            FeatureAuthority.LAGGED_POSTGAME_SOURCE)
    valid.validate_for_prediction()
    for invalid in (
        replace(valid, target_game_realized=True),
        replace(valid, observed_at="2024-09-06T00:30:00Z"),
        replace(valid, authority=FeatureAuthority.TIMING_UNKNOWN),
        replace(valid, authority=FeatureAuthority.PROHIBITED_FOR_TARGET_GAME),
    ):
        with pytest.raises(PlayerTDContractError):
            invalid.validate_for_prediction()


def test_personnel_evidence_preserves_status_without_numeric_effect():
    evidence = PersonnelEvidence(
        "gsis", "AAA", "nflverse injuries", "artifact", "v1",
        "2024-09-05T12:00:00Z", "2024-09-06",
        PersonnelAuthority.PREGAME_RECONSTRUCTABLE, "d" * 64,
        practice_status="LIMITED", game_status="QUESTIONABLE",
    )
    assert evidence.game_status == "QUESTIONABLE"
    assert not any(key in evidence.__dict__ for key in ("penalty", "weight", "adjustment"))


def test_raw_artifact_hash_and_count_are_deterministic_and_secret_free():
    raw = b'{"data":[]}'
    kwargs = {
        "provider": "the-odds-api", "sample_item_id": "item",
        "provider_event_id": None,
        "requested_snapshot": "2024-09-05T12:00:00Z",
        "returned_provider_snapshot": None,
        "acquired_at": "2026-09-22T12:00:00Z", "http_status": 200,
        "request_market": MARKET_KEY, "requested_books": BOOKS,
        "region": "us", "odds_format": "american",
    }
    first = build_raw_artifact_metadata(raw, **kwargs)
    assert first == build_raw_artifact_metadata(raw, **kwargs)
    assert first["raw_byte_count"] == len(raw) and len(first["raw_sha256"]) == 64
    assert not ({"api_key", "authorization", "headers", "url"} & set(first))
    with pytest.raises(PlayerTDContractError, match="secret-bearing"):
        build_raw_artifact_metadata(raw, **kwargs,
                                    request_url="https://example.invalid?apiKey=secret")


def schedule():
    rows = []
    for season in (2023, 2024, 2025):
        rows.extend((
            {"game_id": f"{season}_01_LATE_HOME", "season": season,
             "season_type": "REG", "week": 1, "home_team": "HOME",
             "away_team": "LATE", "kickoff_at": f"{season}-09-08T17:00:00Z"},
            {"game_id": f"{season}_01_EARLY_HOME", "season": season,
             "season_type": "REG", "week": 1, "home_team": "HOME",
             "away_team": "EARLY", "kickoff_at": f"{season}-09-06T00:20:00Z"},
        ))
    return rows


def test_sample_is_deterministic_outcome_free_bounded_and_fixed():
    manifest = build_sample_manifest(schedule())
    assert manifest == build_sample_manifest(list(reversed(schedule())))
    assert len(manifest["items"]) == MAX_REQUEST_COUNT == 6
    assert manifest["estimated_maximum_credits"] == 60
    assert manifest["bulk_acquisition_authorized"] is False
    assert {item["market"] for item in manifest["items"]} == {MARKET_KEY}
    assert {tuple(item["books"]) for item in manifest["items"]} == {BOOKS}
    assert {item["region"] for item in manifest["items"]} == {"us"}
    assert {item["purpose"] for item in manifest["items"]} == {PURPOSE}
    assert all("EARLY" in item["canonical_game_id"] for item in manifest["items"])


def test_sample_outcomes_are_prohibited_and_missing_authority_fails():
    for field in ("touchdown", "final_home_score", "injury_status"):
        with pytest.raises(PlayerTDSampleError, match="outcome"):
            build_sample_manifest([schedule()[0] | {field: True}])
    with pytest.raises(PlayerTDSampleError, match="lacks season 2024"):
        build_sample_manifest([row for row in schedule() if row["season"] != 2024])


def test_sample_readiness_states_are_data_only():
    assert SampleReadiness.NOT_ACQUIRED == "ATTD_SAMPLE_NOT_ACQUIRED"
    assert all("PROFIT" not in state.value and "MODEL" not in state.value for state in SampleReadiness)


def test_offline_modules_have_no_network_or_credentials():
    import gridiron.market.player_td_contract as contract
    import gridiron.market.player_td_identity as identity
    import gridiron.market.player_td_sample as sample
    source = inspect.getsource(contract) + inspect.getsource(identity) + inspect.getsource(sample)
    assert all(token not in source for token in (
        "import requests", "import httpx", "import socket", "GRIDIRON_ODDS_API_KEY",
    ))
