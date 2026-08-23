# ADR-138: Bounded DEF EPA Market-Residual Correction

## Status

Accepted as research candidate.

The selected residual correction cap is 4.25%.

This is not yet a production betting rule.

## Context

Step 90A showed that the aggregate Project Gridiron probability did not add stable predictive value beyond the betting market.

Step 90B decomposed the locked model and identified `def_epa_trend_advantage` as the strongest individual market-residual feature.

Step 90C then tested that signal under stricter robustness conditions.

The research population was narrowed to:

- NFL regular-season games only
- Weeks 1 through 16 only
- tied games excluded
- postseason excluded
- Weeks 17-18 excluded from the core population because of abnormal lineup and incentive risk

Within that population, defensive EPA trend improved Brier score and log loss in each held-out season.

Additional diagnostics showed that very large unconstrained residual adjustments were less stable than moderate corrections.

Step 90D therefore tested whether the DEF EPA residual adjustment should be bounded relative to the market baseline.

## Method

For each held-out season:

- train on the other two seasons
- fit market-only logistic probability
- fit market plus `def_epa_trend_advantage`
- calculate the candidate probability adjustment relative to market
- symmetrically cap that adjustment
- evaluate held-out Brier score and log loss

The core validation seasons were:

- 2022
- 2023
- 2024

The cap search was performed in stages.

Initial caps:

- 0.5%
- 1.0%
- 1.5%
- 2.0%
- 2.5%
- uncapped

Extended caps:

- 3.0%
- 3.5%
- 4.0%
- 5.0%
- 7.5%
- 10.0%
- uncapped

A fine grid was then evaluated:

- 3.25%
- 3.50%
- 3.75%
- 4.00%
- 4.25%
- 4.50%
- 4.75%
- 5.00%

## Selection Rule

The fine-grid selection rule was fixed in code before inspecting the final fine-grid result.

Primary criterion:

- maximize worst-season Brier improvement versus market-only

Tie-breakers:

1. worst-season log-loss improvement
2. mean Brier improvement
3. mean log-loss improvement
4. smaller cap

This conservative rule prioritizes cross-season robustness rather than peak average performance.

## Selected Candidate

The coded selector chose:

`4.25%`

Cross-season summary:

- mean Brier improvement: 0.001117
- worst-season Brier improvement: 0.000922
- mean log-loss improvement: 0.002864
- worst-season log-loss improvement: 0.002531

All improvements are relative to the market-only model.

## Held-Out Behavior

At the selected 4.25% cap, the residual model improved both Brier score and log loss in every held-out season.

### 2022

Brier improvement:

- +0.001346

Log-loss improvement:

- +0.003104

### 2023

Brier improvement:

- +0.000922

Log-loss improvement:

- +0.002531

### 2024

Brier improvement:

- +0.001083

Log-loss improvement:

- +0.002959

The positive values above represent reductions in scoring error relative to market-only probability.

## Interpretation

The evidence supports a bounded market-residual architecture.

The current research result is not:

> Project Gridiron should replace the market probability.

Instead, it is:

> Market probability should remain the primary baseline, while defensive EPA trend may provide a small bounded correction.

The 4.25% cap appears to reduce the instability seen with unrestricted probability movement while retaining the useful portion of the DEF EPA residual signal.

The useful region is broad rather than a razor-thin optimum.

Caps around roughly 3.5%-5.0% all performed well across the held-out seasons.

This plateau is preferable to a highly sensitive single-point optimum.

## Decision

Freeze 4.25% as the Step 90D research candidate.

Do not perform further cap tuning on the 2022-2024 selection population.

Preserve the following core research population:

- regular season only
- Weeks 1-16 only
- no postseason
- Weeks 17-18 excluded from the core residual model

Preserve the architecture:

market probability
→ DEF EPA residual model
→ bounded probability correction

Do not yet use the 4.25% correction for live wagering, staking, or production eligibility.

## Next Step

Step 90E will perform validation of the frozen 4.25% candidate without further tuning.

Priority should be given to a genuinely untouched season or population.

If suitable 2025 historical market and feature data are available, 2025 should be used as the next validation season.

The Step 90E candidate must remain fixed at:

- feature: `def_epa_trend_advantage`
- residual architecture: market plus DEF EPA
- probability adjustment cap: 4.25%
- population: regular season Weeks 1-16

Failure on the untouched validation set should be treated as evidence against promotion rather than a reason to retune the 2022-2024 candidate.
