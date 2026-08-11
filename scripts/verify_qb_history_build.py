from __future__ import annotations

import polars as pl

from gridiron.core.paths import ProjectPaths


def main() -> int:
    paths = ProjectPaths.from_root(".")
    failed = False
    for season in (2022,2023,2024,2025):
        frame = pl.read_parquet(paths.qb_features_file(season))
        nonzero = frame.filter(pl.col("qb_rating_difference") != 0.0).height
        known = int(frame["home_qb_known"].cast(pl.Int64).sum()
                    + frame["away_qb_known"].cast(pl.Int64).sum())
        rate = known / (2 * frame.height)
        print(f"{season}: games={frame.height}, known_rate={rate:.1%}, nonzero_qb_diffs={nonzero}")
        failed |= nonzero == 0 or rate <= 0.50
    print("QB history verification " + ("FAILED" if failed else "PASSED"))
    return 1 if failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
