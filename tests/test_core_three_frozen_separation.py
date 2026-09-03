from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FROZEN_HASHES = {
    "config/step91c_prospective_data_capture_v1.json": "e4d446195a75957c9779a27b282a6fdfc73eea0da34eb6687a3bbc493894a383",
    "config/step91d_prospective_market_ingestion_2026_v1.json": "96a96511972d5d069da811e11e6e10552afa58771683746947495acaa71e8fc8",
    "config/step91h_prospective_integrity_closure_v1.json": "248f4343dda1cdd72c144e71e2cef78e55c0515a36b6b7357b6dd3a3735a13ec",
    "config/step91i_prospective_collection_operations_v1.json": "f3878da02753649c9ef7fd0cf88215d42d980c2aa7c15d824a5085ca8c83839a",
    "src/gridiron/market/prospective_ledger.py": "66ee31db6adc8cb279db492d2eadc9bccfa4aeca30f8b1739f98fbab4b380e30",
    "src/gridiron/market/prospective_market_ingestion.py": "8e3d441dad48dfd7712d575349cd87e9c798b2f8c8ba22b1f67df0862a4df051",
    "src/gridiron/market/prospective_integrity.py": "868247f93a8fbbe9969b5307e77527d1eb038eceba70c2198ca71ae1da9044e1",
    "src/gridiron/market/prospective_operations.py": "1d26d7a4ba0136a1344418dd431d5ee60d3dadf37b53a7720fa319f1520fed6b",
}


def test_selected_frozen_files_remain_byte_identical() -> None:
    for relative, expected in FROZEN_HASHES.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
