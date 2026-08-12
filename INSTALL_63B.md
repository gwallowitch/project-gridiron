# Milestone 63B — Injury Experiment Wiring

Copy these files over the repository root.

Run:

```powershell
python -m ruff check . --fix
python -m ruff check .
python -m pytest
python ship.py research --profile injury_modern
```

Expected research scope: 2022, 2023, 2024 only.

Do not use `--profile modern` for this experiment because 2025 has no verified
injury source timestamp and is intentionally excluded.
