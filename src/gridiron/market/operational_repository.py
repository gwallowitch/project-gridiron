"""Narrow local JSONL repository used as the operational authority."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from gridiron.market.collection_attempts import (
    append_collection_attempt,
    read_collection_attempts,
)
from gridiron.market.operational_history import (
    append_operational_observation,
    read_operational_history,
)
from gridiron.market.operational_totals import (
    append_totals_observation,
    read_totals_history,
)
from gridiron.market.totals_collection_attempts import (
    append_totals_attempt,
    read_totals_attempts,
)


class JsonlOperationalEvidenceRepository:
    """Typed façade over the unchanged Step 91Q/R JSONL persistence functions."""

    def __init__(
        self,
        *,
        moneyline_history: Path | str,
        moneyline_attempts: Path | str,
        totals_history: Path | str,
        totals_attempts: Path | str,
    ) -> None:
        self.moneyline_history = Path(moneyline_history)
        self.moneyline_attempts = Path(moneyline_attempts)
        self.totals_history = Path(totals_history)
        self.totals_attempts = Path(totals_attempts)

    def read_moneyline_observations(self) -> tuple[dict[str, Any], ...]:
        return read_operational_history(self.moneyline_history)

    def read_moneyline_attempts(self) -> tuple[dict[str, Any], ...]:
        return read_collection_attempts(self.moneyline_attempts)

    def append_moneyline_observation(self, prediction: Mapping[str, Any]) -> dict[str, Any]:
        return append_operational_observation(self.moneyline_history, prediction)

    def append_moneyline_attempt(self, attempt: Mapping[str, Any]) -> None:
        append_collection_attempt(self.moneyline_attempts, attempt)

    def read_totals_observations(self) -> tuple[dict[str, Any], ...]:
        return read_totals_history(self.totals_history)

    def read_totals_attempts(self) -> tuple[dict[str, Any], ...]:
        return read_totals_attempts(self.totals_attempts)

    def append_totals_observation(self, observation: Mapping[str, Any]) -> None:
        append_totals_observation(self.totals_history, observation)

    def append_totals_attempt(self, attempt: Mapping[str, Any]) -> None:
        append_totals_attempt(self.totals_attempts, attempt)
