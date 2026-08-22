# ADR-121 — Play-Consistency Historical Validation

Step 87A produced four-season play-consistency artifacts with approximately
94.4% full-season coverage and complete Week 2+ history.

Step 87B is the technical gate before the final standalone feature research
screen.

The validation requires:

- expected schedule row counts;
- unique game IDs;
- Week 1 completely unknown;
- essentially complete Week 2+ both-team history;
- at least 94% full-season coverage;
- non-zero feature dispersion;
- no non-finite feature values;
- all component rates within [0, 1];
- no feature nulls when both teams are marked known.

A PASS permits Step 87C experiment wiring. It does not imply predictive value.
