# ADR-091 — Travel Fatigue Experiment Wiring

Step 81B passed the technical historical gate. Step 81C therefore introduces
two isolated candidate families: away travel miles (scaled per 1000 miles) and
absolute time-zone shift. Positive weights penalize away-team travel burden.

The six promoted weights remain frozen at 0.20, 10.0, 0.24, 1.0, 5.25, and
2.25. Short-week interactions are deliberately deferred. Any apparent winner
must pass Step 81D robustness before promotion consideration.
