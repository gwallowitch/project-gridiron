# ADR-084: Defensive Schedule Difficulty Robustness

Step 79D confirmed that defensive schedule difficulty contains some useful
signal, but the best numerical score at higher weights came with a larger
winner-accuracy penalty.

79E therefore freezes a small candidate region:

- baseline 0.00
- 1.50
- 2.00
- 2.25
- 2.50
- 2.75

The promoted five-weight baseline remains unchanged.

79E evaluates:
- mean paired score delta;
- mean winner-accuracy delta;
- season W-L-T;
- leave-one-season-out mean deltas;
- worst leave-one-season-out degradation.

A candidate may receive `PROVISIONAL_PASS` only if score improvement persists
across at least three of four leave-one-season-out views, worst-case LOOSO
degradation is controlled, and mean winner-accuracy loss is no worse than
0.2 percentage points.

If 79E produces `PROVISIONAL_PASS`, Step 79F should perform the formal
baseline-vs-six-weight promotion lock. Otherwise defensive SOS is held or
parked.
