# Project Gridiron — PGR v1 Milestone

Copy the contents of this folder over the repository root:

```text
C:\Users\grego\Desktop\ProjectGridiron\project-gridiron
```

Preserve the directory structure and replace existing files when prompted.
Do not copy the outer `Project_Gridiron_PGR_v1_Milestone` directory itself
inside the repository.

## Validation

Run from the repository root with the virtual environment active:

```powershell
python -m ruff check .
python -m pytest
python -m gridiron.cli --help
python -m gridiron.cli build-pgr --season 2025
Get-Item .\data\curated\pgr\pgr_2025.parquet
python -m gridiron.cli run-season --season 2025
```

Expected test total: approximately **121 passed** (104 existing plus 17 PGR tests).

The CLI help should include `build-pgr`, and the full season summary should
include `Project Gridiron Rating` as the seventh stage.

## PGR v1 Formula

```text
schedule_adjustment = 0.50 × (strength_of_schedule_rating − 100)
pgr_rating = performance_rating + schedule_adjustment
```

PGR v1 is a transparent baseline, not a calibrated point-spread estimate.
