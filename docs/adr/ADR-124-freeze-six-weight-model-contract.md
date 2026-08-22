# ADR-124 — Freeze the Six-Weight Model Contract

## Context

Standalone feature discovery closed after Step 87. Multiple recent feature
families were technically valid but failed to produce practical out-of-sample
improvement.

The project now needs a stable model contract before calibration, walk-forward
validation, and market comparison begin.

## Decision

Step 88A freezes and verifies the six active research weights:

- rest = 0.20;
- offensive sack = 10.0;
- punt return = 0.24;
- long-field avoidance = 1.0;
- defensive EPA trend = 5.25;
- defensive schedule difficulty = 2.25.

Home-field advantage remains 1.5 and probability scale remains 0.14.

All recent rejected research families must remain zero.

The validator produces a SHA-256 fingerprint over the locked contract so later
steps can detect accidental model drift.

## Consequence

A Step 88A PASS means the feature-discovery model is frozen. Step 88B can then
evaluate historical combined-model behavior without ambiguity about which
features are active.
