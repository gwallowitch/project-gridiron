# ADR-147: Step 91F Prospective Evidence Accumulation

## Status

Accepted.

## Context

The prospective pipeline is operational but needs a narrow interface for accumulating
genuine 2026 observations, preserving non-bets, settling decisions, tracking the
200-settlement gate, and exposing missing protocol components without tuning.

## Decision

Add a Step 91F operational layer that accepts only explicitly classified real
prospective snapshots and delegates capture to Step 91D/91C. Settlement delegates to
Step 91C and therefore uses immutable decision-time DraftKings prices. Summary and
validation are read-only and deterministic. Test fixtures remain outside operational
capture and are never research evidence.

The documented failure gate can be evaluated once 200 bets settle. Promotion requires
the documented profit, ROI, edge-trim, and season conditions. Because no authoritative
edge-trim thresholds exist, Step 91F reports protocol status `INCOMPLETE` and cannot
declare promotion from real evidence. It does not invent thresholds.

## Consequences

All decisions, eligible bets, non-bets, settlements, unsettled bets, outcomes, profit,
ROI, probability scores, edges, offered prices, and season progress remain auditable.
No historical observation is relabelled, no frozen candidate component changes, and no
Titan compatibility is fabricated for the absent Titan artifacts.
