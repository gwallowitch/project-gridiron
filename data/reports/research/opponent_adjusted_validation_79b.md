# Step 79B — Opponent-Adjusted Historical Validation

This is a technical coverage/dispersion gate only. It does not claim predictive lift.

## Coverage

| Season | Rows | Both known | Week 4+ both known |
| ---: | ---: | ---: | ---: |
| 2022 | 284 | 88.7% | 100.0% |
| 2023 | 285 | 88.8% | 100.0% |
| 2024 | 285 | 88.8% | 100.0% |
| 2025 | 285 | 88.8% | 100.0% |

## Feature dispersion

| Season | Feature | Coverage | Mean | Std | P05 | Median | P95 | Non-zero |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022 | `opponent_adjusted_off_epa_difference` | 94.4% | 0.0013 | 0.1143 | -0.1765 | 0.0000 | 0.1827 | 94.0% |
| 2022 | `opponent_adjusted_def_epa_difference` | 94.4% | 0.0034 | 0.0990 | -0.1697 | 0.0044 | 0.1616 | 94.0% |
| 2022 | `offensive_schedule_difficulty_advantage` | 94.4% | -0.0021 | 0.0609 | -0.0999 | -0.0011 | 0.0799 | 100.0% |
| 2022 | `defensive_schedule_difficulty_advantage` | 94.4% | 0.0040 | 0.0712 | -0.0745 | 0.0018 | 0.0935 | 100.0% |
| 2023 | `opponent_adjusted_off_epa_difference` | 94.4% | 0.0047 | 0.1365 | -0.2189 | 0.0000 | 0.2354 | 94.1% |
| 2023 | `opponent_adjusted_def_epa_difference` | 94.4% | 0.0040 | 0.1061 | -0.1845 | 0.0000 | 0.1741 | 94.1% |
| 2023 | `offensive_schedule_difficulty_advantage` | 94.4% | 0.0020 | 0.0836 | -0.1014 | 0.0000 | 0.1014 | 100.0% |
| 2023 | `defensive_schedule_difficulty_advantage` | 94.4% | -0.0037 | 0.1007 | -0.1349 | 0.0017 | 0.1103 | 100.0% |
| 2024 | `opponent_adjusted_off_epa_difference` | 94.4% | 0.0037 | 0.1480 | -0.2182 | 0.0000 | 0.2509 | 94.1% |
| 2024 | `opponent_adjusted_def_epa_difference` | 94.4% | 0.0036 | 0.1129 | -0.1693 | 0.0000 | 0.1834 | 94.1% |
| 2024 | `offensive_schedule_difficulty_advantage` | 94.4% | -0.0019 | 0.0908 | -0.1152 | -0.0001 | 0.1120 | 100.0% |
| 2024 | `defensive_schedule_difficulty_advantage` | 94.4% | 0.0043 | 0.0882 | -0.1139 | 0.0013 | 0.1344 | 100.0% |
| 2025 | `opponent_adjusted_off_epa_difference` | 94.4% | -0.0048 | 0.1401 | -0.2354 | 0.0000 | 0.2297 | 94.1% |
| 2025 | `opponent_adjusted_def_epa_difference` | 94.4% | -0.0020 | 0.1136 | -0.1885 | 0.0000 | 0.1862 | 94.1% |
| 2025 | `offensive_schedule_difficulty_advantage` | 94.4% | -0.0037 | 0.0835 | -0.0903 | -0.0025 | 0.0971 | 100.0% |
| 2025 | `defensive_schedule_difficulty_advantage` | 94.4% | 0.0038 | 0.0753 | -0.0925 | 0.0023 | 0.1265 | 100.0% |

## Gate

**PASS** — the opponent-adjusted family is technically healthy enough for controlled experiment wiring.

A PASS here means only that the artifacts are researchable. It does not promote any opponent-adjusted signal.
