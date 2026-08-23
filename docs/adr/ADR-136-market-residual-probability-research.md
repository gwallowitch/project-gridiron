# ADR-136: Market-Residual Probability Research

## Status

Accepted — research checkpoint.

## Context

Step 89 established a historical NFL moneyline research pipeline using:

- Project Gridiron historical predictions,
- temperature-calibrated model probabilities,
- historical moneyline prices,
- vig-free market probabilities,
- settled game outcomes, and
- configurable edge / expected-ROI thresholds.

Initial historical betting research showed that the locked Gridiron aggregate
probability did not produce profitable moneyline selections across the tested
threshold grid.

Additional diagnostics showed that the historical betting market was materially
stronger at selecting winners than the locked Gridiron model, particularly when
the two disagreed.

Step 90A therefore asks a narrower question:

> Does the locked Gridiron probability contain incremental predictive
> information after the market probability is already known?

This is a residual-information question rather than a direct betting-strategy
test.

## Research Population

The experiment uses settled NFL games from:

- 2022: 282 games
- 2023: 285 games
- 2024: 285 games

Total:

- 852 settled games

The two tied 2022 games are excluded because they cannot be settled as standard
moneyline wins or losses.

## Inputs

Each observation contains:

- season,
- game identifier,
- vig-free market home-win probability,
- calibrated Gridiron home-win probability, and
- actual binary home-win outcome.

The Gridiron probability uses the locked temperature-calibration contract.

## Method

Three logistic probability models are compared:

1. market only,
2. Gridiron only,
3. market + Gridiron.

Evaluation uses leave-one-season-out validation:

- train 2023 + 2024, test 2022,
- train 2022 + 2024, test 2023,
- train 2022 + 2023, test 2024.

Primary evaluation metrics are:

- Brier score,
- log loss, and
- winner accuracy.

Lower Brier score and log loss are better.

The combined-model coefficients are also inspected to determine whether the
Gridiron probability contributes a stable positive signal after controlling for
the market probability.

## Results

### Held-out 2022

Market only:

- accuracy: 65.957%
- Brier: 0.209500
- log loss: 0.605239

Gridiron only:

- accuracy: 58.156%
- Brier: 0.230872
- log loss: 0.652504

Market + Gridiron:

- accuracy: 66.312%
- Brier: 0.209222
- log loss: 0.604687

Combined versus market:

- accuracy: +0.355 percentage points
- Brier: -0.000278
- log loss: -0.000552

Combined coefficients:

- market: 5.276424
- Gridiron: -0.259907
- intercept: -2.512125

The combined model produces a very small held-out improvement, but the Gridiron
coefficient is negative.

### Held-out 2023

Market only:

- accuracy: 67.719%
- Brier: 0.219813
- log loss: 0.631247

Gridiron only:

- accuracy: 59.298%
- Brier: 0.239210
- log loss: 0.670735

Market + Gridiron:

- accuracy: 67.719%
- Brier: 0.219864
- log loss: 0.631361

Combined versus market:

- accuracy: +0.000 percentage points
- Brier: +0.000052
- log loss: +0.000114

Combined coefficients:

- market: 5.546876
- Gridiron: 0.028302
- intercept: -2.809619

The Gridiron contribution is effectively zero and the combined model is
slightly worse on both probability-scoring metrics.

### Held-out 2024

Market only:

- accuracy: 71.579%
- Brier: 0.199621
- log loss: 0.586769

Gridiron only:

- accuracy: 65.263%
- Brier: 0.218266
- log loss: 0.626832

Market + Gridiron:

- accuracy: 70.877%
- Brier: 0.203109
- log loss: 0.594757

Combined versus market:

- accuracy: -0.702 percentage points
- Brier: +0.003488
- log loss: +0.007988

Combined coefficients:

- market: 5.703020
- Gridiron: -1.735228
- intercept: -1.945782

Adding Gridiron materially worsens the held-out 2024 result.

## Interpretation

The locked aggregate Gridiron probability does not demonstrate stable
incremental predictive value after the market probability is known.

Across the three held-out seasons:

- 2022 shows only a very small improvement,
- 2023 is effectively neutral to slightly worse,
- 2024 is clearly worse.

The Gridiron coefficient is also not stable:

- negative in 2022,
- approximately zero in 2023,
- strongly negative in 2024.

This is inconsistent with a robust independent probability signal.

The result does not establish that the underlying Gridiron football features
contain no useful information.

Instead, it shows that the current locked aggregate probability is not an
effective way to extract incremental information relative to the betting
market.

## Decision

Do not promote the locked aggregate Gridiron probability as a market-beating
moneyline signal.

Do not continue tuning betting thresholds around the aggregate probability.

Preserve the existing locked model as a historical research baseline.

Proceed to feature-level market-residual research.

The next research phase should test whether individual Gridiron feature families
contain incremental information after controlling for the market probability.

Candidate feature-level models should use the same leakage-safe
leave-one-season-out structure and compare:

- market only,
- market + individual feature or feature family.

Features should advance only when held-out probability metrics provide
repeatable evidence of incremental value.

## Consequences

Project Gridiron shifts from:

> Can the existing aggregate model beat moneyline prices?

to:

> Which football information, if any, adds predictive information beyond what
> the market already knows?

This avoids discarding potentially useful football features merely because the
current aggregate weighting scheme underperforms the market.

It also establishes the market probability as the primary benchmark for future
moneyline research.

## Next Step

Step 90B: feature-level market-residual research.
