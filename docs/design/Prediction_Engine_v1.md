# Prediction Engine v1

Prediction Engine v1 produces an expected home margin and win probabilities from prior-week PGR values.

- Rating difference = home PGR - away PGR + home-field advantage
- Expected home margin = rating difference
- Home win probability = logistic(rating difference)
- Confidence is based on the favored team's probability

This release intentionally excludes injuries, weather, rest, travel, and market lines. Those features require backtesting before inclusion.
