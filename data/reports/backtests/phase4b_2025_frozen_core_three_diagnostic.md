# Step 91O Phase 4B — 2025 Frozen Core-Three Historical Diagnostic

**Classification: HISTORICAL DIAGNOSTIC — NOT PROSPECTIVE EVIDENCE**

## Population

- Source rows: 285
- 2025 regular-season games: 272
- Diagnostic rows: 256
- Excluded rows: 16
- Ties: 1
- Population: complete-feature Weeks 2-18; all 16 Week 1 games excluded.
- Includes Weeks 17-18; NOT a frozen Weeks 1-16 eligibility replay.

## Frozen Candidate

- Market coefficient: 4.980172
- DEF EPA coefficient: 1.044827
- Intercept: -2.514766
- Residual cap: ±4.25%
- Market books: BetMGM / FanDuel / DraftKings
- Weight: 1/3 each

## Results

| Model | N | Accuracy | Brier | Log loss |
|---|---:|---:|---:|---:|
| Frozen candidate | 255 | 0.6392 | 0.2147 | 0.6141 |
| Core-Three market only | 255 | 0.6471 | 0.2133 | 0.6101 |
| Legacy v2 reference | 255 | 0.6000 | 0.2359 | 0.6689 |

## Interpretation Boundary

This complete-feature Weeks 2-18 diagnostic applies only the frozen numerical transformation, not the frozen Weeks 1-16 eligibility population or Week 1 neutral-feature policy. No model was fitted or recalibrated.

The historical market and EPA provenance limitations identified by Step 91O Phase 4A remain unresolved. Therefore these results must not be treated as leakage-safe validation or prospective evidence.

## Files

- `data\reports\backtests\phase4b_2025_frozen_core_three_diagnostic.json`
- `data\reports\backtests\phase4b_2025_frozen_core_three_diagnostic.md`
- `data\reports\backtests\phase4b_2025_frozen_core_three_diagnostic_rows.csv`
