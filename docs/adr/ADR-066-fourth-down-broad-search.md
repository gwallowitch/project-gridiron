# ADR-066: Fourth-Down Broad Search

75D tests fourth-down features independently on top of the Step 74F research
lock: rest 0.20, offensive sack 10.0, punt return 0.24, and long-field
avoidance 1.00.

The grid contains one baseline plus 20 candidates:
- offense EPA: 0.5, 1.0, 1.5, 2.0
- defense EPA: 0.5, 1.0, 1.5, 2.0
- conversion rate: 2, 4, 6, 8
- defensive stop rate: 2, 4, 6, 8
- short-yardage conversion: 1, 2, 4, 6

Only one fourth-down research weight is active per candidate. Missing team
history is neutral-filled to zero through the existing research join helper.
75E is only justified if 75D shows credible incremental value against the
approximately 0.4668 locked benchmark.
