# Step 91H Prospective Evidence Integrity Closure

## Result

The frozen candidate is unchanged and the operational protocol is **READY FOR
PROSPECTIVE EVIDENCE COLLECTION**. No real or synthetic evidence is included.

Step 91H adds a complete scheduled-game denominator, retained reason-coded attempts,
environment-generated UTC receipt time, content-addressed raw artifacts, an offline
SHA256 event chain and export digest, frozen provenance/correction rules, freshness,
identity, kickoff, settlement-completeness, trim, diagnostic, season-completion, and
probability-metric definitions.

## Prospectively frozen assumptions

No repository convention fixed capture timing or quote age. Before evidence begins,
Step 91H therefore predeclares one capture at 60 minutes before kickoff with a 55-65
minute acceptance window, retries only inside that window, no replacement after an
accepted attempt, and a uniform 10-minute maximum quote age. The settlement deadline
is 48 hours after an official final result. These values were not selected from 2026
outcomes or historical profitability.

Kickoff uses a retained NFL official schedule artifact; settlement uses a retained NFL
official final gamebook/result artifact. Corrections append separately and never rewrite
decision inputs. DEF EPA uses source `project-gridiron-def-epa-trend`, calculation
identity `frozen-input-v1`, and receipt-time cutoff; Week 1 null becomes 0.0 and later
missing values reject.

## Closure definitions

Edge trims use the global population of 2026 settled eligible HOME/AWAY bets, full
precision edge descending, then `observation_id` ascending, removing
`floor(n × fraction)` for 1%, 5%, and 10%. Pushes/cancellations are excluded and all
three retained populations must have strictly positive profit. This outcome-blind tie
rule is newly frozen before evidence; it is not claimed as recovered history.

Balanced means home market probability in `[0.45, 0.55]`; above is favorite and below
is underdog. This is diagnostic only. Brier/log loss use home probability for every
accepted decision with a HOME/AWAY outcome, including non-bets or missing execution
prices; pushes, cancellations, and unsettled decisions are excluded.

A season is complete only when every registered Weeks 1-16 game has a terminal capture
status, no postponement remains unresolved, every completed accepted decision is
settled, and no settlement is overdue. Cancelled games remain in the denominator.

## Limitations

Local receipt time is not cryptographic proof of external chronology. The offline hash
chain detects modification, insertion, deletion, or reordering within the retained
chain but cannot prevent deletion of the entire file. External publication is supported
by a deterministic digest but is not fabricated here.
