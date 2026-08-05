# Project Gridiron Experiment Framework v1

The framework evaluates candidate prediction parameters without modifying the
production prediction engine defaults.

## Candidate parameters
- Home-field advantage
- Logistic probability scale
- Margin scale
- Margin intercept

## Selection score
Lower is better:

`Brier + 0.25 × LogLoss + 0.01 × MarginRMSE − 0.10 × Accuracy`

The individual metrics remain visible and should be reviewed before promoting a
candidate. The score is a ranking convenience, not proof of statistical
significance.

## Outputs
`ship.py experiment --season YEAR` prints ranked results and appends them to:

`data/reports/experiments/experiment_registry.json`
