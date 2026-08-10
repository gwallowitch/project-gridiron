# 62B wiring fixes

Copy this package over the repository root.

Run the patch script once:

```powershell
python scripts/apply_62b_baseline_fixes.py
```

Then validate:

```powershell
python -m ruff check . --fix
python -m ruff check .
python -m pytest
python ship.py research --profile modern
```

This fixes:

- QB artifacts being required in old zero-QB-weight tests.
- Research code hard-coding `rest_000_baseline`.
- QB research now inferring `qb_000_baseline`.
