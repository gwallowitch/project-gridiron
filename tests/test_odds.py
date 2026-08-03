from __future__ import annotations

import unittest

from gridiron.markets.odds import (
    american_to_decimal,
    american_to_implied_probability,
    expected_profit_per_unit,
    fractional_kelly,
    remove_two_way_margin,
)


class OddsTests(unittest.TestCase):
    def test_converts_positive_american_odds(self) -> None:
        self.assertAlmostEqual(american_to_decimal(200), 3.0)

    def test_converts_negative_american_odds(self) -> None:
        self.assertAlmostEqual(american_to_decimal(-110), 1.9090909091)

    def test_rejects_zero_american_odds(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot be zero"):
            american_to_decimal(0)

    def test_implied_probability_at_minus_110(self) -> None:
        self.assertAlmostEqual(american_to_implied_probability(-110), 11 / 21)

    def test_removes_balanced_two_way_margin(self) -> None:
        market = remove_two_way_margin(-110, -110)
        self.assertAlmostEqual(market.first, 0.5)
        self.assertAlmostEqual(market.second, 0.5)
        self.assertAlmostEqual(market.first + market.second, 1.0)
        self.assertGreater(market.overround, 0.0)

    def test_positive_expected_value(self) -> None:
        self.assertGreater(expected_profit_per_unit(0.60, -110), 0.0)

    def test_negative_expected_value(self) -> None:
        self.assertLess(expected_profit_per_unit(0.40, -110), 0.0)

    def test_fractional_kelly_returns_zero_without_edge(self) -> None:
        self.assertEqual(fractional_kelly(0.40, -110), 0.0)

    def test_fractional_kelly_respects_cap(self) -> None:
        self.assertEqual(fractional_kelly(0.80, 100, fraction=1.0, cap=0.01), 0.01)

    def test_rejects_invalid_probability(self) -> None:
        with self.assertRaisesRegex(ValueError, "Probability"):
            expected_profit_per_unit(1.01, -110)


if __name__ == "__main__":
    unittest.main()

