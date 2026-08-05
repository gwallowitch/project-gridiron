# Install v0.8.0a Experiment Framework

Copy this release folder's contents over the Project Gridiron repository root.
Do not copy the release directory itself as a nested repository folder.

Run:

```powershell
python -m ruff check . --fix
python -m ruff check .
python -m pytest
python ship.py season --season 2025
python ship.py experiment --season 2025
```
