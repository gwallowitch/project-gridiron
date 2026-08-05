# Installation

Copy the contents of this release folder over the Project Gridiron
repository root and replace existing files.

Run:

```powershell
python -m ruff check . --fix
python -m ruff check .
python -m pytest
python ship.py research --profile modern
```

The modern profile requires complete persisted inputs for 2022–2025.
Run each season pipeline first if those files do not already exist:

```powershell
python ship.py season --season 2022
python ship.py season --season 2023
python ship.py season --season 2024
python ship.py season --season 2025
```
