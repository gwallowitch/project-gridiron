# Step 91O Phase 4C — 2025 Diagnostic Performance Breakdown

**Classification: HISTORICAL DIAGNOSTIC — NOT PROSPECTIVE EVIDENCE**

## Population

- Input diagnostic rows: 256
- Non-tied scoring rows (all calculations): 255
- Week 1 excluded: 16 (no prior-season DEF EPA feature)
- Ties excluded: 1

## Overall

| Model | N | Accuracy | Brier | Log loss |
|---|---:|---:|---:|---:|
| frozen_candidate | 255 | 0.6392 | 0.2147 | 0.6141 |
| core_three_market | 255 | 0.6471 | 0.2133 | 0.6101 |
| legacy_v2 | 255 | 0.6000 | 0.2359 | 0.6689 |

## Candidate vs Core-Three Market

- Prediction disagreements: 4 (1.6%)
- Candidate correct on disagreements: 1
- Market correct on disagreements: 3

## DEF EPA Adjustment

- Mean absolute probability change: 0.024135
- Median absolute probability change: 0.022923
- Maximum absolute probability change: 0.042500
- Positive adjustments: 120
- Negative adjustments: 135
- Zero adjustments: 0

## Candidate Probability Calibration

| Band | N | Predicted | Observed |
|---|---:|---:|---:|
| 0%-50% | 108 | 0.3274 | 0.3796 |
| 50%-60% | 34 | 0.5601 | 0.4412 |
| 60%-70% | 40 | 0.6499 | 0.5500 |
| 70%-80% | 38 | 0.7534 | 0.7632 |
| 80%-90% | 34 | 0.8552 | 0.8529 |
| 90%-100% | 1 | 0.9024 | 1.0000 |

## Core-Three Market Calibration

| Band | N | Predicted | Observed |
|---|---:|---:|---:|
| 0%-50% | 106 | 0.3451 | 0.3679 |
| 50%-60% | 37 | 0.5523 | 0.4865 |
| 60%-70% | 43 | 0.6426 | 0.5814 |
| 70%-80% | 41 | 0.7439 | 0.6829 |
| 80%-90% | 23 | 0.8595 | 0.9565 |
| 90%-100% | 5 | 0.9095 | 1.0000 |

## Weekly Accuracy

| Week | N | Candidate Acc. | Market Acc. | Candidate Brier | Market Brier |
|---:|---:|---:|---:|---:|---:|
| 2 | 16 | 0.6250 | 0.6250 | 0.1741 | 0.1774 |
| 3 | 16 | 0.7500 | 0.7500 | 0.2074 | 0.2060 |
| 4 | 15 | 0.6667 | 0.6667 | 0.2010 | 0.1986 |
| 5 | 14 | 0.2857 | 0.2857 | 0.3569 | 0.3296 |
| 6 | 15 | 0.7333 | 0.7333 | 0.1982 | 0.2030 |
| 7 | 15 | 0.7333 | 0.8000 | 0.1753 | 0.1751 |
| 8 | 13 | 0.7692 | 0.7692 | 0.1734 | 0.1765 |
| 9 | 14 | 0.5714 | 0.5714 | 0.2752 | 0.2666 |
| 10 | 14 | 0.7143 | 0.7143 | 0.2027 | 0.2046 |
| 11 | 15 | 0.7333 | 0.7333 | 0.1807 | 0.1817 |
| 12 | 14 | 0.7143 | 0.7857 | 0.1641 | 0.1587 |
| 13 | 16 | 0.5625 | 0.5625 | 0.2553 | 0.2494 |
| 14 | 14 | 0.5000 | 0.5714 | 0.2418 | 0.2427 |
| 15 | 16 | 0.6250 | 0.6250 | 0.1970 | 0.1968 |
| 16 | 16 | 0.6875 | 0.6250 | 0.2092 | 0.2254 |
| 17 | 16 | 0.5625 | 0.5625 | 0.2340 | 0.2384 |
| 18 | 16 | 0.6250 | 0.6250 | 0.2101 | 0.1990 |

## Largest DEF EPA Moves

| Game | Week | Market P | DEF EPA | Candidate P | Delta | Outcome |
|---|---:|---:|---:|---:|---:|---|
| 2025_06_LA_BAL | 6 | 0.2786 | -0.0830 | 0.2361 | -0.0425 | AWAY |
| 2025_10_DET_WAS | 10 | 0.2137 | -0.2998 | 0.1712 | -0.0425 | AWAY |
| 2025_11_GB_NYG | 11 | 0.2492 | -0.1894 | 0.2067 | -0.0425 | AWAY |
| 2025_11_HOU_TEN | 11 | 0.2827 | -0.0687 | 0.2402 | -0.0425 | AWAY |
| 2025_11_BAL_CLE | 11 | 0.2151 | -0.1592 | 0.1726 | -0.0425 | AWAY |
| 2025_13_JAX_TEN | 13 | 0.2922 | -0.1188 | 0.2497 | -0.0425 | AWAY |
| 2025_13_DEN_WAS | 13 | 0.2807 | -0.1520 | 0.2382 | -0.0425 | AWAY |
| 2025_14_SEA_ATL | 14 | 0.2560 | -0.1493 | 0.2135 | -0.0425 | AWAY |
| 2025_16_PHI_WAS | 16 | 0.2444 | -0.1537 | 0.2019 | -0.0425 | AWAY |
| 2025_05_DEN_PHI | 5 | 0.6407 | 0.1257 | 0.6832 | +0.0425 | AWAY |
| 2025_05_WAS_LAC | 5 | 0.6348 | 0.2022 | 0.6773 | +0.0425 | AWAY |
| 2025_05_KC_JAX | 5 | 0.3640 | -0.1468 | 0.3215 | -0.0425 | HOME |
| 2025_06_NE_NO | 6 | 0.3773 | -0.0498 | 0.3348 | -0.0425 | AWAY |
| 2025_06_BUF_ATL | 6 | 0.3559 | -0.1298 | 0.3134 | -0.0425 | HOME |
| 2025_07_PIT_CIN | 7 | 0.3158 | -0.1507 | 0.2733 | -0.0425 | HOME |
| 2025_07_LA_JAX | 7 | 0.4016 | -0.1170 | 0.3591 | -0.0425 | AWAY |
| 2025_07_PHI_MIN | 7 | 0.4332 | -0.1816 | 0.3907 | -0.0425 | AWAY |
| 2025_07_TB_DET | 7 | 0.7082 | 0.1266 | 0.7507 | +0.0425 | HOME |
| 2025_07_HOU_SEA | 7 | 0.6018 | -0.2688 | 0.5593 | -0.0425 | HOME |
| 2025_08_CHI_BAL | 8 | 0.4956 | -0.1401 | 0.4531 | -0.0425 | HOME |

## Interpretation Boundary

- No model was fitted or recalibrated.
- Frozen coefficients and residual cap were unchanged.
- Historical market/EPA provenance limitations from Phase 4A remain unresolved.
- This is diagnostic analysis only.
- It is not leakage-safe validation or prospective evidence.
