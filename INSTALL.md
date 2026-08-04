# Install Benchmark Milestone

Copy the contents of this release folder over the root of the current `project-gridiron` repository, preserving the directory structure.

Run:

```powershell
python -m ruff check .
python -m pytest
python ship.py benchmark --season 2025
```

The benchmark command requires an existing `data/curated/pgr/pgr_<season>.parquet` file. Run the season pipeline first if it is missing.
