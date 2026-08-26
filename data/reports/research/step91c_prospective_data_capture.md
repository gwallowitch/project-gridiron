# Step 91C Prospective Data Capture

## Outcome

Step 91C converts the frozen Step 91B prospective protocol into an operational,
append-only evidence ledger. It does not tune the candidate or advance to live market
ingestion.

## Frozen protocol

- Protocol: `step91b-prospective-validation-v1`
- Candidate: `market-plus-def-epa-capped-0425-v1`
- Logistic coefficients: market `+4.980172`, DEF EPA `+1.044827`, intercept
  `-2.514766`
- Symmetric residual cap: `0.0425`
- Window: 2026 `REG`, Weeks 1-16
- Consensus: Bet365, SI, Betway, BetMGM, FanDuel, Caesars, DraftKings
- Execution: DraftKings
- Eligibility: edge must be strictly greater than zero

## Event contract

`DECISION` captures the pre-kickoff timestamps, complete seven-book market snapshot,
DEF EPA value, consensus and candidate probabilities, selected side, captured
DraftKings price, break-even probability, edge, and bet eligibility. Week 1 substitutes
`0.0` only when DEF EPA is unavailable. Later missing DEF EPA rejects capture. If the
selected execution price is unavailable, the event remains a non-bet with null
break-even probability and edge.

`SETTLEMENT` references the decision identity and settles only from its captured
price. Wins use American-odds unit profit, losses are `-1`, and non-bets are `0`.
Unsettled bets remain outside settled profit.

Canonical serialization plus SHA-256 provides deterministic observation and event
identity. Full replay rejects duplicate decisions, orphan or duplicate settlements,
and modified settlement facts.

## Operation

```text
python scripts/step91c_ledger.py --ledger data/prospective/2026.jsonl capture --input decision.json
python scripts/step91c_ledger.py --ledger data/prospective/2026.jsonl validate
python scripts/step91c_ledger.py --ledger data/prospective/2026.jsonl settle --game-id GAME_ID --result HOME --settled-at TIMESTAMP
python scripts/step91c_ledger.py --ledger data/prospective/2026.jsonl summary
```

The ledger is JSON Lines and is only opened in append mode after the complete prior
history plus proposed event validates.
