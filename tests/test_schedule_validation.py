from __future__ import annotations

import unittest
from dataclasses import dataclass

from gridiron.data.nflverse import _normalize_seasons
from gridiron.validation.schedules import validate_schedule


@dataclass
class FakeFrame:
    columns: list[str]
    height: int


VALID_COLUMNS = [
    "game_id",
    "season",
    "week",
    "game_type",
    "gameday",
    "away_team",
    "home_team",
]


class ScheduleValidationTests(unittest.TestCase):
    def test_schedule_accepts_required_schema(self) -> None:
        validate_schedule(FakeFrame(columns=VALID_COLUMNS, height=272))

    def test_schedule_rejects_missing_column(self) -> None:
        with self.assertRaisesRegex(ValueError, "home_team"):
            validate_schedule(FakeFrame(columns=VALID_COLUMNS[:-1], height=272))

    def test_schedule_rejects_empty_data(self) -> None:
        with self.assertRaisesRegex(ValueError, "no games"):
            validate_schedule(FakeFrame(columns=VALID_COLUMNS, height=0))

    def test_seasons_are_deduplicated_and_sorted(self) -> None:
        self.assertEqual(_normalize_seasons([2025, 2023, 2025]), [2023, 2025])

    def test_seasons_cannot_be_empty(self) -> None:
        with self.assertRaisesRegex(ValueError, "At least one"):
            _normalize_seasons([])


if __name__ == "__main__":
    unittest.main()
