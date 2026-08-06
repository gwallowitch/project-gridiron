# Quarterback Intelligence 62A

## Configuration

- `config/qb_ratings.csv`
- `config/qb_starters.csv`

Both files may be header-only. Unknown quarterbacks receive a neutral
rating of zero.

## Output

`data/curated/qb_features/qb_features_<season>.parquet`

## Columns

- `home_qb`
- `away_qb`
- `home_qb_rating`
- `away_qb_rating`
- `qb_rating_difference`
- `home_qb_known`
- `away_qb_known`

## Next phase

62B will add `qb_weight` to the experiment framework without changing the
production prediction engine.
