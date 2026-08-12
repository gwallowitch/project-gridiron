# Milestone 63A — Injury Availability Foundation

Copy over the repository root, then run:

```powershell
python -m ruff check . --fix
python -m ruff check .
python -m pytest
```

Build real historical artifacts locally:

```powershell
python -c "from gridiron.pipelines.injury_features import run_injury_features_pipeline; [print(run_injury_features_pipeline(s)) for s in (2022, 2023, 2024, 2025)]"
```

Inspect coverage:

```powershell
python -c "import polars as pl; [print(s, pl.read_parquet(f'data/curated/injury_features/injury_features_{s}.parquet').select(pl.col('home_injury_known').mean().alias('home_known'),pl.col('away_injury_known').mean().alias('away_known'),pl.col('kickoff_guard_applied').all().alias('kickoff_guard')).row(0,named=True)) for s in (2022,2023,2024,2025)]"
```

Do not wire this feature into experiments yet.
