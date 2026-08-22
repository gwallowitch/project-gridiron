# Step 80B — Penalty Discipline Historical Validation

This is a technical coverage/dispersion gate only. It does not claim predictive lift.

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
| 2022 | `penalty_yards_discipline_advantage` | 94.4% | -1.4212 | 20.8473 | -35.4231 | -0.0381 | 27.1451 | 100.0% |
| 2022 | `penalty_rate_discipline_advantage` | 94.4% | -0.1908 | 2.2144 | -3.4028 | -0.0430 | 2.8750 | 100.0% |
| 2022 | `offensive_penalty_discipline_advantage` | 94.4% | -0.4586 | 12.3906 | -20.4014 | -0.3204 | 19.0061 | 100.0% |
| 2022 | `defensive_penalty_discipline_advantage` | 94.4% | -0.9625 | 16.8283 | -24.5684 | -0.4279 | 22.1216 | 100.0% |
| 2023 | `penalty_yards_discipline_advantage` | 94.4% | 0.0521 | 19.2043 | -29.1445 | -0.3023 | 29.3445 | 100.0% |
| 2023 | `penalty_rate_discipline_advantage` | 94.4% | 0.0362 | 1.9002 | -3.0853 | 0.0877 | 2.8514 | 100.0% |
| 2023 | `offensive_penalty_discipline_advantage` | 94.4% | 0.2439 | 11.2620 | -17.8624 | -0.2230 | 16.3795 | 100.0% |
| 2023 | `defensive_penalty_discipline_advantage` | 94.4% | -0.1918 | 14.9076 | -25.2890 | -0.5866 | 21.6708 | 100.0% |
| 2024 | `penalty_yards_discipline_advantage` | 94.4% | 0.1648 | 21.8136 | -37.8095 | 0.5810 | 31.7686 | 100.0% |
| 2024 | `penalty_rate_discipline_advantage` | 94.4% | 0.0089 | 2.1211 | -3.5691 | 0.1291 | 3.2299 | 100.0% |
| 2024 | `offensive_penalty_discipline_advantage` | 94.4% | -0.0915 | 14.7821 | -23.9140 | 0.2050 | 25.2305 | 100.0% |
| 2024 | `defensive_penalty_discipline_advantage` | 94.4% | 0.2563 | 17.1434 | -25.2733 | 0.6443 | 26.0171 | 100.0% |
| 2025 | `penalty_yards_discipline_advantage` | 94.4% | -0.1959 | 20.8487 | -29.2951 | -0.7674 | 26.9904 | 100.0% |
| 2025 | `penalty_rate_discipline_advantage` | 94.4% | -0.0211 | 2.2248 | -3.6176 | -0.0399 | 3.1410 | 100.0% |
| 2025 | `offensive_penalty_discipline_advantage` | 94.4% | -0.3144 | 14.0519 | -21.3469 | 0.2127 | 21.8681 | 100.0% |
| 2025 | `defensive_penalty_discipline_advantage` | 94.4% | 0.1186 | 15.5005 | -20.2884 | -0.9437 | 19.3827 | 100.0% |

## Gate

**PASS** — the penalty-discipline family is technically healthy enough for controlled experiment wiring.

A PASS means the artifacts are researchable. It does not promote any penalty-discipline signal.
