# Step 78B — Recent-Form Historical Validation

This report validates coverage and dispersion only. It does not claim predictive value.

## Coverage

| Season | Rows | Both known | Week 3+ both known |
| ---: | ---: | ---: | ---: |
| 2022 | 284 | 88.7% | 100.0% |
| 2023 | 285 | 88.8% | 100.0% |
| 2024 | 285 | 88.8% | 100.0% |
| 2025 | 285 | 88.8% | 100.0% |

## Feature dispersion

| Season | Feature | Coverage | Mean | Std | P05 | Median | P95 | Non-zero |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022 | `recent_off_epa_difference` | 94.4% | 0.0045 | 0.1829 | -0.2629 | 0.0061 | 0.3132 | 100.0% |
| 2022 | `recent_def_epa_advantage` | 94.4% | -0.0027 | 0.1727 | -0.2738 | -0.0075 | 0.2558 | 100.0% |
| 2022 | `off_epa_trend_difference` | 94.4% | 0.0011 | 0.1149 | -0.1972 | 0.0000 | 0.2027 | 82.1% |
| 2022 | `def_epa_trend_advantage` | 94.4% | -0.0021 | 0.1242 | -0.2075 | 0.0000 | 0.2336 | 82.1% |
| 2022 | `off_success_trend_difference` | 94.4% | -0.0016 | 0.0466 | -0.0956 | 0.0000 | 0.0737 | 82.1% |
| 2022 | `def_success_trend_advantage` | 94.4% | 0.0006 | 0.0509 | -0.0825 | 0.0000 | 0.0897 | 82.1% |
| 2023 | `recent_off_epa_difference` | 94.4% | 0.0010 | 0.2039 | -0.3361 | -0.0016 | 0.3374 | 100.0% |
| 2023 | `recent_def_epa_advantage` | 94.4% | 0.0066 | 0.1889 | -0.2771 | -0.0106 | 0.3434 | 100.0% |
| 2023 | `off_epa_trend_difference` | 94.4% | -0.0017 | 0.1104 | -0.1933 | 0.0000 | 0.1744 | 82.2% |
| 2023 | `def_epa_trend_advantage` | 94.4% | -0.0011 | 0.1369 | -0.2316 | 0.0000 | 0.2370 | 82.2% |
| 2023 | `off_success_trend_difference` | 94.4% | -0.0002 | 0.0431 | -0.0752 | 0.0000 | 0.0743 | 82.2% |
| 2023 | `def_success_trend_advantage` | 94.4% | -0.0005 | 0.0475 | -0.0738 | 0.0000 | 0.0783 | 82.2% |
| 2024 | `recent_off_epa_difference` | 94.4% | 0.0032 | 0.2080 | -0.3309 | 0.0059 | 0.3649 | 100.0% |
| 2024 | `recent_def_epa_advantage` | 94.4% | 0.0054 | 0.1935 | -0.2966 | 0.0133 | 0.3138 | 100.0% |
| 2024 | `off_epa_trend_difference` | 94.4% | -0.0024 | 0.1196 | -0.2162 | 0.0000 | 0.1895 | 82.2% |
| 2024 | `def_epa_trend_advantage` | 94.4% | 0.0061 | 0.1337 | -0.2292 | 0.0000 | 0.2478 | 82.2% |
| 2024 | `off_success_trend_difference` | 94.4% | -0.0019 | 0.0474 | -0.0807 | 0.0000 | 0.0787 | 82.2% |
| 2024 | `def_success_trend_advantage` | 94.4% | 0.0016 | 0.0492 | -0.0860 | 0.0000 | 0.0895 | 82.2% |
| 2025 | `recent_off_epa_difference` | 94.4% | 0.0003 | 0.2163 | -0.3712 | 0.0160 | 0.3293 | 100.0% |
| 2025 | `recent_def_epa_advantage` | 94.4% | 0.0043 | 0.2093 | -0.3498 | 0.0070 | 0.3506 | 100.0% |
| 2025 | `off_epa_trend_difference` | 94.4% | 0.0014 | 0.1259 | -0.1943 | 0.0000 | 0.2154 | 82.2% |
| 2025 | `def_epa_trend_advantage` | 94.4% | 0.0102 | 0.1343 | -0.1937 | 0.0000 | 0.2214 | 82.2% |
| 2025 | `off_success_trend_difference` | 94.4% | 0.0001 | 0.0465 | -0.0707 | 0.0000 | 0.0763 | 82.2% |
| 2025 | `def_success_trend_advantage` | 94.4% | 0.0016 | 0.0478 | -0.0791 | 0.0000 | 0.0840 | 82.2% |

## Gate

**PASS** — historical coverage and dispersion are healthy enough to proceed to controlled experiment wiring.

Passing this gate means the feature family is technically researchable. It does **not** promote any recent-form signal.
