# ADR-137: Feature-Level Market-Residual Research

## Status

Accepted as research evidence.

`def_epa_trend_advantage` advances to Step 90C robustness research.

No feature or combination evaluated in this step is promoted directly into the production betting model.

## Context

Step 90A tested whether the aggregate Project Gridiron probability added predictive information beyond historical NFL moneyline market probabilities.

Across leave-one-season-out validation for 2022-2024, the aggregate Gridiron probability did not demonstrate stable incremental value beyond the market.

Step 90B therefore decomposed the locked six-weight model and tested the six underlying feature advantages individually against the market.

The historical population contained 852 settled games from the 2022, 2023, and 2024 seasons.

The six evaluated features were:

- `rest_advantage`
- `off_sack_rate_advantage`
- `punt_return_advantage`
- `long_field_avoidance_advantage`
- `def_epa_trend_advantage`
- `defensive_schedule_difficulty_advantage`

Each feature was evaluated using leave-one-season-out logistic probability research with market probability retained as the baseline predictor.

## Results

### Defensive EPA trend

`def_epa_trend_advantage` produced the strongest and most consistent market-residual evidence.

Its fitted feature coefficient remained positive in every held-out season:

- 2022: +0.650754
- 2023: +0.660656
- 2024: +0.951012

Relative to market-only probability, log loss improved in all three held-out seasons:

- 2022: -0.001463
- 2023: -0.001904
- 2024: -0.000150

Brier score improved in 2022 and 2023:

- 2022: -0.000559
- 2023: -0.000738

The 2024 Brier score worsened slightly:

- 2024: +0.000084

Accuracy was not consistently improved, so the feature is not considered production-ready.

The repeatable probability-quality improvement and stable coefficient direction are sufficient to advance the feature to robustness research.

### Defensive schedule difficulty

`defensive_schedule_difficulty_advantage` retained a positive coefficient in all three held-out seasons but did not produce stable probability improvement.

It improved Brier score and log loss in 2022 and 2024 but materially worsened both metrics in 2023.

The feature remains a secondary research candidate but does not advance as an independent residual signal.

### Remaining four features

The following features did not demonstrate sufficient stable incremental predictive value beyond the market:

- `rest_advantage`
- `off_sack_rate_advantage`
- `punt_return_advantage`
- `long_field_avoidance_advantage`

They do not advance from this residual screen.

This decision concerns their usefulness as independent market-residual probability features. It does not by itself invalidate their historical role elsewhere in Project Gridiron.

## Two-Feature Interaction Test

A follow-up experiment compared:

1. market only
2. market plus defensive EPA trend
3. market plus defensive schedule difficulty
4. market plus both features

The combined model improved over market-only probability in 2022 and 2024.

However, the combined model materially deteriorated in the 2023 held-out season.

Relative to defensive EPA trend alone in 2023, adding defensive schedule difficulty changed:

- accuracy: -1.053 percentage points
- Brier score: +0.001680
- log loss: +0.004533

The two-feature model therefore does not demonstrate sufficient cross-season stability for promotion.

## Decision

Advance only:

`def_epa_trend_advantage`

to Step 90C robustness research.

Park:

`defensive_schedule_difficulty_advantage`

as a secondary research candidate.

Do not promote the two-feature combination.

Do not promote any Step 90B result directly into production betting eligibility, staking, or probability generation.

## Step 90C Requirements

Step 90C will test whether the defensive EPA trend residual signal survives additional out-of-sample and population robustness checks.

At minimum, research should examine:

- chronological or expanding-window validation
- early-season versus later-season behavior
- regular-season versus postseason behavior where sample size permits
- market favorite/underdog probability ranges
- coefficient direction and magnitude stability
- Brier score and log-loss stability

A production decision requires evidence beyond the three-season Step 90B screen.

## Consequences

Project Gridiron's aggregate probability is not assumed to outperform the market.

Market probability remains the benchmark for residual research.

The project will concentrate additional research on the specific football information that demonstrates repeatable incremental signal rather than attempting to force the complete locked feature model into a betting strategy.

The six-weight historical configuration remains preserved as prior research state and is not modified by this ADR.
