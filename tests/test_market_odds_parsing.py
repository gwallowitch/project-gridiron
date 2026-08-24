from __future__ import annotations

import pytest

from gridiron.market.odds_parsing import parse_american_odds


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("EVEN", 100),
        ("even", 100),
        ("EV", 100),
        ("EVS", 100),
        ("+120", 120),
        ("-135", -135),
        (110, 110),
        (-150, -150),
        (125.0, 125),
    ],
)
def test_parse_american_odds(
    value: object,
    expected: int,
) -> None:
    assert parse_american_odds(value) == expected
