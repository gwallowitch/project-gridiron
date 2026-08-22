from gridiron.weather.stadiums import stadium_for_team


def test_known_team_has_stadium() -> None:
    location = stadium_for_team("BUF")
    assert location is not None
    assert 40.0 < location.latitude < 45.0


def test_alias_resolves() -> None:
    assert stadium_for_team("WSH") == stadium_for_team("WAS")


def test_unknown_team_returns_none() -> None:
    assert stadium_for_team("XXX") is None
