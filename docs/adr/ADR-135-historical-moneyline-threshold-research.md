# ADR-135: Historical Moneyline Threshold Research

## Status

Accepted

## Context

Step 89F evaluated whether the calibrated Project Gridiron football model could
produce historically profitable NFL moneyline selections by applying minimum
model-market edge and expected-ROI thresholds.

The research population combined Project Gridiron historical prediction
artifacts with historical moneyline data for the 2022 through 2024 NFL seasons.

Tied games were excluded because they cannot be settled as ordinary two-outcome
moneyline results.

The resulting population contained 852 settled games:

- 2022: 282
- 2023: 285
- 2024: 285

Model probabilities were calibrated using the locked Step 88E temperature
calibration contract before comparison with vig-free market probabilities.

## Results

The tested standalone threshold grid did not identify a profitable historical
betting region.

Across the population:

- Project Gridiron winner accuracy: 60.68%
- market-favorite winner accuracy: 68.08%
- model/market agreement games: 673
- model/market disagreement games: 179

When the model and market agreed, the shared selection won 68.05% of games.

When they disagreed:

- Project Gridiron accuracy: 32.96%
- market accuracy: 67.04%

Disagreement performance by absolute model-market probability gap was:

| Probability gap | Games | Gridiron accuracy | Market accuracy |
| --- | ---: | ---: | ---: |
| <5% | 10 | 20.00% | 80.00% |
| 5-10% | 39 | 46.15% | 53.85% |
| 10-15% | 37 | 21.62% | 78.38% |
| 15-20% | 40 | 35.00% | 65.00% |
| 20%+ | 53 | 32.08% | 67.92% |

No tested disagreement-gap bucket outperformed the market.

The historical edge/expected-ROI threshold sweep likewise produced negative
realized ROI throughout the tested grid.

## Decision

No standalone Project Gridiron moneyline betting threshold is qualified from
Step 89F.

Further threshold optimization against the existing standalone probability
model is stopped.

The negative result is retained as a research finding rather than treated as a
software failure.

## Architectural Consequence

Project Gridiron will pivot from treating its football probability as an
independent replacement for the market probability.

Step 90 will investigate a market-relative architecture in which the vig-free
market probability acts as a baseline and Project Gridiron attempts to identify
incremental predictive information or residual market error.

The first Step 90 experiment must test whether Project Gridiron's calibrated
probability contributes predictive information after market probability is
already known.

Evaluation must use held-out historical seasons rather than fitting and
evaluating a combination on the same population.

## Boundaries

Step 89F does not:

- select production betting thresholds
- authorize real-money betting
- define Kelly sizing
- define bankroll allocation
- optimize a betting portfolio
- modify the locked six-weight football model
- modify the Step 88E temperature calibration contract

Those decisions require subsequent market-relative research.
