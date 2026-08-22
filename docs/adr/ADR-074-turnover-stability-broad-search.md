# ADR-074: Turnover-Stability Broad Search

77D evaluates seven turnover-stability signals on top of the four-weight
research lock: rest 0.20, offensive sack 10.0, punt return 0.24, long-field
avoidance 1.00. Rejected fourth-down and explosive-suppression families remain
parked at zero.

The grid contains one baseline plus 28 candidates:
- turnover protection: 10, 20, 30, 40
- takeaway creation: 10, 20, 30, 40
- interception protection: 10, 20, 30, 40
- interception creation: 10, 20, 30, 40
- offensive fumble luck: 0.5, 1, 2, 4
- defensive fumble luck: 0.5, 1, 2, 4
- combined fumble luck: 0.25, 0.5, 1, 2

Only one turnover-stability weight is active per candidate. The fumble grids
use smaller multipliers because recovery-rate features have much larger raw
dispersion.

77E fine tuning is justified only if 77D shows credible improvement over the
~0.4668 locked benchmark without unacceptable winner-accuracy degradation.
