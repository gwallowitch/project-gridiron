# Rest Differential v1

## Purpose

Measure the scheduling-rest context available to each team before a game.

## Formula

`rest_advantage = home_rest_days - away_rest_days`

Positive values favor the home team. Negative values favor the away team.

## Inputs

The schedule dataset must contain:

- `game_id`
- `season`
- `week`
- `gameday`
- `home_team`
- `away_team`

## Output

`data/curated/rest_features/rest_features_<season>.parquet`

## Initial behavior

The season pipeline creates and validates rest features, but Prediction
Engine v2 does not consume them yet. A later controlled experiment will
test candidate rest weights before any production promotion.
