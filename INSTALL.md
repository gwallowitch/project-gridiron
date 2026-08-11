# 62C hotfix

Copy over the repository root, then run:

```powershell
python -m ruff check . --fix
python -m ruff check .
python -m pytest
python scripts/build_historical_qb_intelligence.py
python scripts/verify_qb_history_build.py
```

Only if verification passes:

```powershell
python ship.py research --profile modern
```

Fixes nflreadpy `passing_interceptions` and double-normalization.
