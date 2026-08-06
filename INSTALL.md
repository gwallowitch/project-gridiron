# Installation

Copy this release over the repository root. Then run:

```powershell
python -m ruff check . --fix
python -m ruff check .
python -m pytest
python scripts/review_promotion.py --profile modern
```

This writes promotion records under `data/reports/promotions/` and does not modify production settings.
