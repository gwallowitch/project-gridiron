# Step 81B — Travel Fatigue Historical Validation

This gate validates technical coverage, dispersion, and site-risk only. It does not claim predictive value.

## Season health

| Season | Rows | Geography known | Rest known | Avg miles | P95 miles | Avg TZ shift |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022 | 284 | 100.0% | 100.0% | 877.2 | 2151.5 | 0.84 |
| 2023 | 285 | 100.0% | 100.0% | 998.4 | 2329.3 | 1.05 |
| 2024 | 285 | 100.0% | 100.0% | 970.1 | 2315.7 | 0.99 |
| 2025 | 285 | 100.0% | 100.0% | 987.1 | 2319.6 | 1.02 |

## Neutral / international-site audit

- **2022:** neutral=0, international=4, neutral column=None
- **2023:** neutral=0, international=3, neutral column=None
- **2024:** neutral=0, international=3, neutral column=None
- **2025:** neutral=0, international=0, neutral column=None

## Gate

**PASS** — ordinary travel features are technically suitable for controlled research.

### Warnings

- 2022: venue audit found 0 neutral and 4 international-site rows
- 2023: venue audit found 0 neutral and 3 international-site rows
- 2024: venue audit found 0 neutral and 3 international-site rows

International/neutral-site rows should be excluded or venue-corrected before wiring travel distance if the audit identifies material mismatches.
