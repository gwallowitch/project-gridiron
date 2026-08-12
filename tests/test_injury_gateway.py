from __future__ import annotations

from gridiron.data.nflverse import NFLVerseGateway


class Client:
    def load_injuries(self, seasons):
        return seasons

def test_gateway_loads_injuries() -> None:
    assert NFLVerseGateway(Client()).injuries([2024,2024]) == [2024]
