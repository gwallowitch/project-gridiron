# ADR-139: Untouched 2025 DEF EPA Residual Validation

## Status

Accepted.

Step 90E validates the frozen bounded DEF EPA market-residual candidate on the previously untouched 2025 NFL regular season.

## Background

Steps 90B through 90D identified and tested a market-residual probability architecture using historical seasons 2022-2024.

The frozen candidate entering Step 90E was:

- baseline: market-implied home win probability
- residual feature: `def_epa_trend_advantage`
- architecture: market probability plus DEF EPA residual model
- probability adjustment cap: 4.25%
- population: regular season only
- eligible weeks: Weeks 1-16
- postseason: excluded
- Weeks 17-18: excluded
- Week 1 unavailable DEF EPA values: neutralized to 0.0

The 4.25% cap was selected before inspecting 2025 validation performance.

No 2025 outcomes were used to select the feature, architecture, cap, or core population.

## Validation Data

The untouched validation population was the 2025 NFL regular season through Week 16.

Total games:

- 240

Market probabilities were constructed from a seven-book consensus.

Books:

- Bet365
- SI
- Betway
- BetMGM
- FanDuel
- Caesars
- DraftKings

For each game:

1. each sportsbook's two-sided moneyline was converted to a no-vig home win probability
2. the seven no-vig probabilities were averaged
3. the resulting consensus probability was used as the market input

Pre-reveal auditing confirmed:

- 240 Gridiron REG Weeks 1-16 games
- 240 market REG Weeks 1-16 games
- 240 joined games
- zero missing market probabilities
- seven books for every market observation
- zero duplicate market keys
- 16 missing DEF EPA observations
- all 16 missing DEF EPA observations occurred in Week 1

The Week 1 DEF EPA observations were assigned the predetermined neutral value of 0.0.

## Training Population

The frozen residual model was fit using:

- 2022 REG Weeks 1-16
- 2023 REG Weeks 1-16
- 2024 REG Weeks 1-16

The resulting coefficients entering the untouched 2025 evaluation were:

- market coefficient: +4.980172
- DEF EPA coefficient: +1.044827
- intercept: -2.514766

The DEF EPA coefficient remained positive.

## Untouched 2025 Results

### Market Only

Accuracy:

- 65.833%

Brier score:

- 0.210636

Log loss:

- 0.607685

### Frozen 4.25% Capped DEF EPA Residual

Accuracy:

- 65.833%

Brier score:

- 0.210145

Log loss:

- 0.606282

### Difference Versus Market Only

Accuracy:

- +0.000 percentage points

Brier score:

- -0.000491

Log loss:

- -0.001403

Negative Brier and log-loss deltas represent improved probability scoring.

## Interpretation

Step 90E passes.

The frozen DEF EPA residual candidate improved both proper probability scoring metrics on a previously untouched season.

The candidate did not improve classification accuracy.

That distinction is important.

The objective of the residual architecture is not primarily to change predicted winners. It is to determine whether Project Gridiron contains information that improves probability estimates beyond the market baseline.

On the untouched 2025 population:

- winner classification was unchanged
- Brier score improved
- log loss improved

This is consistent with a small probability refinement rather than a replacement for the market's directional prediction.

The 2025 improvement was smaller than some of the improvements observed during 2022-2024 research.

That is not grounds for retuning.

The important result is that the direction of the probability-scoring improvement survived untouched validation.

## Decision

Step 90E is recorded as:

**PASS**

Freeze the candidate architecture:

market probability
→ DEF EPA residual model
→ symmetric 4.25% maximum probability correction

Preserve:

- feature: `def_epa_trend_advantage`
- cap: 4.25%
- regular season only
- Weeks 1-16 only
- postseason excluded
- Weeks 17-18 excluded from the core model
- unavailable Week 1 DEF EPA treated as neutral

Do not retune the cap or feature based on the 2025 validation result.

## Validation Burn Rule

The 2025 season is now considered consumed validation data for this candidate.

It may be used for:

- reporting
- diagnostics
- fixed-rule economic evaluation
- understanding behavior of the already-frozen candidate

It must not be used to:

- retune the 4.25% cap
- select a replacement DEF EPA feature
- optimize feature coefficients specifically for 2025
- redefine the core population because of observed 2025 outcomes
- repeatedly search candidate architectures until 2025 performance improves

Any future architecture change influenced by 2025 results requires a new untouched validation population before promotion.

## Production Status

Step 90E does not authorize live wagering.

The result establishes evidence that the frozen residual architecture improves probability quality beyond the market baseline.

Economic usefulness remains unproven.

## Next Step

Step 90F will evaluate the economic meaning of the frozen residual signal.

Step 90F must preserve:

- DEF EPA as the residual feature
- 4.25% probability cap
- REG Weeks 1-16 population
- existing market-residual architecture

Step 90F may examine fixed-rule diagnostics including:

- magnitude of residual adjustment
- direction of residual adjustment
- market probability bands
- realized outcomes by residual-edge bucket
- candidate probability versus available market price
- whether larger residual signals correspond to stronger realized performance
- whether apparent edge survives vig

Step 90F is an evaluation step, not another opportunity to tune the Step 90E candidate.

No staking or bankroll rules should be optimized until economic edge has been established.
