# ADR-010: Statistical Promotion Review

## Status

Accepted

## Decision

Use paired season-level differences versus the baseline. Report mean,
median, sample standard deviation, deterministic percentile-bootstrap 95%
confidence intervals, and win/loss/tie records.

Promotion outcomes are PASS, INCONCLUSIVE, or REJECT. A PASS requires a
practical score improvement, a confidence interval below zero, more season
wins than losses, at least four seasons, and no material accuracy loss.

With only four modern seasons, this remains a decision aid rather than proof
of future generalization.
