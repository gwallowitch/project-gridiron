# Step 91F Prospective Evidence Accumulation and Protocol Completeness

## Outcome

Step 91F provides a deterministic operational interface for genuine 2026 evidence:
Step 91D snapshot ingestion, Step 91C immutable decision capture and settlement,
validation, evidence summaries, gate progress, and protocol-completeness reporting.
It delegates all candidate calculations and ledger mutation to the frozen code.

## Current evidence

There are no repository prospective snapshots or ledger events. Current counts are
zero decisions, zero eligible bets, zero non-bets, and zero settlements. Economic
values with no sample are null rather than evidence-like zeros. The gate is
**INCONCLUSIVE**, with 200 settled bets remaining.

Operational capture accepts only the explicit classification `REAL PROSPECTIVE DATA`.
Synthetic mechanics fixtures are isolated to temporary test directories, are marked
`TEST FIXTURES / SYNTHETIC DATA`, and never enter the committed research report.

## Protocol completeness

Candidate identity/version, coefficients, residual cap, books, DraftKings execution,
strictly positive edge, 2026 REG Weeks 1-16, timestamp and settlement rules, primary
metrics, 200-bet minimum, failure/promotion gates, and season robustness are available.
Authoritative edge-trim thresholds are absent, so completeness is **INCOMPLETE** and a
promotion declaration is blocked. No thresholds were selected or inferred.

`docs/TITAN_SPEC.md`, `titan/`, and `run_core50.py` are absent. Step 91F adds no Titan
compatibility.

## CLI

```text
python scripts/step91f_prospective_evidence.py --ledger data/prospective/2026.jsonl capture --input snapshot.json
python scripts/step91f_prospective_evidence.py --ledger data/prospective/2026.jsonl settle --game-id GAME --result HOME --settled-at TIMESTAMP
python scripts/step91f_prospective_evidence.py --ledger data/prospective/2026.jsonl validate
python scripts/step91f_prospective_evidence.py --ledger data/prospective/2026.jsonl summary
python scripts/step91f_prospective_evidence.py --ledger data/prospective/2026.jsonl protocol
```

Output is canonical compact JSON. Step 91F performs no network collection, historical
backfill, model tuning, alternative threshold search, observation deletion, or ledger
rewrite.
