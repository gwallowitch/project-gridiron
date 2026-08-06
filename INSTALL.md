# Installation

Copy this release folder's contents over the Project Gridiron repository
root.

Run:

```powershell
python -m ruff check . --fix
python -m ruff check .
python -m pytest
python -c "from gridiron.pipelines.qb_features import run_qb_features_pipeline; print(run_qb_features_pipeline(2025))"
```

Inspect the output:

```powershell
python -c "import polars as pl; print(pl.read_parquet('data/curated/qb_features/qb_features_2025.parquet').head())"
```

The provided QB CSV files are header-only, so the initial dataset will use
neutral unknown-quarterback defaults until starter and rating data are
added.
