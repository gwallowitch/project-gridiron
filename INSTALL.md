# Installation

Copy the contents of this release folder over the Project Gridiron
repository root. Preserve the directory structure and replace existing
files when prompted.

Run:

```powershell
python -m ruff check . --fix
python -m ruff check .
python -m pytest
python ship.py season --season 2025
```

Verify:

```powershell
Get-Item .\data\curated\rest_features\rest_features_2025.parquet
```
