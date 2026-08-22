# ADR-112 — Isolated Performance-Stability Screen

Step 84B passed the historical validation gate with:

- 100% Week 2 recent-margin availability;
- 100% Week 3+ stability availability;
- approximately 88.8% full-season stability coverage;
- approximately 94.4% recent-margin and close-game coverage.

Step 84C therefore introduces three isolated research families:

1. performance stability — lower point-differential volatility is favorable;
2. recent margin — stronger recent point differential is favorable;
3. close-game experience — higher recent close-game rate is tested as a
   separate signal.

All previously rejected travel, weather, and pace weights remain zero.

The weight ranges are deliberately conservative and scale-aware. No promotion
occurs in Step 84C. The research output determines whether Step 84D narrows a
winner or parks the family.
