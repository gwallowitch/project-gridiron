# Step 84B â€” Performance Stability Historical Validation

This report validates coverage, dispersion, chronology, and no-leakage behavior. It does not claim predictive value.

## Coverage

| Season | Rows | Week1 unknown | Week2 margin known | Week2 stability unknown | Week3+ stability known | Stability cov | Margin cov | Close cov |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022 | 284 | yes | 100.0% | yes | 100.0% | 88.7% | 94.4% | 94.4% |
| 2023 | 285 | yes | 100.0% | yes | 100.0% | 88.8% | 94.4% | 94.4% |
| 2024 | 285 | yes | 100.0% | yes | 100.0% | 88.8% | 94.4% | 94.4% |
| 2025 | 285 | yes | 100.0% | yes | 100.0% | 88.8% | 94.4% | 94.4% |

## Leakage contract

All Step 84A features are derived from completed prior games only. Current-game scores must not contribute to pregame features for that same game.

Week 1 is intentionally unknown. Margin and close-game features become available after one prior game. Stability standard deviation becomes available only after two prior games.

## Gate

**PASS** â€” the performance-stability family is technically researchable.
