# Historical Backtesting v1

## Purpose
Measure Prediction Engine v1 against completed NFL games without introducing future information into the original predictions.

## Inputs
- `data/curated/predictions/predictions_<season>.parquet`
- `data/raw/schedules/schedules_<season>.parquet`

The schedule must contain `home_score` and `away_score` for completed games.

## Outputs
- Evaluated game-level Parquet: `data/curated/backtests/backtest_<season>.parquet`
- JSON and Markdown reports under `data/reports/backtests/`
- DuckDB metadata record with dataset name `backtests`

## Metrics
- Winner accuracy
- Prediction coverage
- Brier score
- Binary log loss
- Margin MAE and RMSE
- Home-pick and away-pick accuracy
- Fixed probability calibration buckets

## Limitations
The initial release evaluates one season and one persisted prediction model. Parameter tuning and multi-season model comparisons are deliberately deferred.
