# Step 83B â€” Pace / Tempo Historical Validation

This report validates coverage, dispersion, and leakage safety. It does not claim predictive value.

## Coverage

| Season | Rows | Week1 unknown | Week2+ both-known | Volume cov | Seconds cov | Tempo cov |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022 | 284 | yes | 100.0% | 94.4% | 94.4% | 94.4% |
| 2023 | 285 | yes | 100.0% | 94.4% | 94.4% | 94.4% |
| 2024 | 285 | yes | 100.0% | 94.4% | 94.4% | 94.4% |
| 2025 | 285 | yes | 100.0% | 94.4% | 94.4% | 94.4% |

## Leakage contract

Step 83A uses prior games only. Current-game pace observations must not contribute to that game's pregame features.

Week 1 is intentionally unknown. From Week 2 onward, prior-game history is permitted.

## Gate

**FAIL**
- 2022: pace_seconds_advantage has no dispersion
- 2022: tempo_index_advantage contains non-finite values
- 2023: pace_seconds_advantage has no dispersion
- 2023: tempo_index_advantage contains non-finite values
- 2024: pace_seconds_advantage has no dispersion
- 2024: tempo_index_advantage contains non-finite values
- 2025: pace_seconds_advantage has no dispersion
- 2025: tempo_index_advantage contains non-finite values
