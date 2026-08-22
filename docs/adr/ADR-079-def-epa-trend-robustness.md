# ADR-079: Defensive EPA Trend Robustness Validation

78F identified a stable local optimum around 5.0–5.5, with 5.25 producing the
best aggregate result against the correct four-weight baseline.

78G freezes the search to baseline, 5.00, 5.25, and 5.50. It does not perform
additional numerical tuning.

After the 16 research runs, `validate_step78g_robustness.py` evaluates:
- mean paired score delta;
- mean winner-accuracy delta;
- season W-L-T;
- leave-one-season-out mean score deltas;
- worst leave-one-season-out degradation.

A candidate may receive `PROVISIONAL_PASS` only when its aggregate improvement
persists across at least three of four leave-one-season-out views, its worst
leave-one-out result is controlled, and winner accuracy is not materially
degraded.

This is a robustness gate, not the permanent production lock.
