# ADR-068: Explosive-Suppression Historical Validation

76B validates 2022–2025 artifacts before model wiring. Gates:
- home/away known coverage >= 90%
- feature coverage >= 85%
- average prior-history depth >= 5 weeks
- average offensive scrimmage-play sample >= 150
- average defensive scrimmage-play sample >= 150
- all five features must have usable observations and non-zero dispersion

These are data-quality gates only. 76B does not alter model weights, runtime
scoring, or `config/experiments.toml`.
