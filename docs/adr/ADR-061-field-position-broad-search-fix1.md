# ADR-061 Fix 1: Corrected 74D Runtime Wiring

The initial 74D patcher contained an over-escaped regular expression and failed before changing the research grid. FIX1 removes that regex strategy and applies explicit fail-fast replacements against the known 73D experiment and research runner contracts.

The patch is transactional: if any expected anchor is missing, both runners and `config/experiments.toml` are restored.
