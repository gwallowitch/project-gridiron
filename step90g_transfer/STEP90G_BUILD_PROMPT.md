Build Step 90G: Economic Robustness of the frozen DEF EPA residual.

Create:
- src/gridiron/market/economic_robustness.py
- tests/test_market_economic_robustness.py
- docs/adr/ADR-140-economic-robustness-of-frozen-def-epa-residual.md

Context:
Step 90D froze the DEF EPA residual probability cap at 4.25%.
Step 90E validated that frozen candidate on untouched 2025 REG Weeks 1-16.
Step 90F evaluated actual DraftKings economic performance:
- 240 games
- 112 positive-edge observations
- +5.772 flat profit
- +5.15% ROI

Step 90F.5 showed noisy threshold behavior:
- >0%: +5.15% ROI
- >=1%: +6.43%
- >=2%: +7.47%
- >=3%: -8.15%
- >=4%: +15.94%
- >=5%: +26.16%

Therefore Step 90G MUST NOT optimize a betting threshold or residual cap.

Objective:
Try to break the frozen 2025 economic result through robustness diagnostics.

Requirements:

1. Frozen candidate
- Use the existing FROZEN_RESIDUAL_CAP.
- It must remain 4.25%.
- Do not introduce another residual-cap parameter.
- Do not select a new betting threshold.
- Primary economic population remains positive offered-price edge (>0%).

2. Execution-book robustness
Evaluate the same frozen candidate using available execution prices:
- DraftKings
- FanDuel
- Caesars
- BetMGM
- Bet365
- Betway
- SI
- ESPN
- opener

For each report:
- bets
- wins
- win rate
- mean edge
- profit
- ROI

Do not change the model or market consensus between execution books.

3. Leave-one-book-out market robustness
The seven-book fair consensus remains the baseline.
For each constituent book:
- remove that book from the consensus
- recompute fair market probability
- retain the frozen DEF EPA model and 4.25% cap
- evaluate the positive-edge economic population

This is diagnostic only. Do not select the best consensus.

4. Edge-tail robustness
Evaluate:
- all positive edges
- excluding largest 1%
- excluding largest 5%
- excluding largest 10%

Do not call any slice the preferred strategy.

5. Season timing
Evaluate:
- Weeks 1-4
- Weeks 5-8
- Weeks 9-12
- Weeks 13-16

6. Market-side robustness
Evaluate:
- favorites
- underdogs
- approximately balanced games using existing project conventions if available.

Do not invent a threshold to improve results.

7. Metrics
Reuse existing economic helpers where possible:
- bets
- wins
- win rate
- mean edge
- profit
- ROI

Use existing drawdown/losing-streak helpers if already available.

8. Tests
Create deterministic tests covering:
- frozen 4.25% cap
- book execution evaluation
- empty populations
- positive-edge filtering
- leave-one-book-out behavior
- edge-tail exclusion
- season slices
- favorite/underdog slices
- profit/ROI calculations

No network calls.

9. Research integrity
Explicitly enforce:
- no cap tuning
- no betting-threshold tuning
- no model retuning
- no sportsbook selection based on highest observed ROI
- no production wagering promotion

10. ADR-140
Document:
- frozen 4.25% cap
- frozen 2025 REG Weeks 1-16 population
- DraftKings +5.15% baseline ROI
- why threshold optimization is prohibited
- all robustness dimensions
- interpretation rules
- research-only status

11. Code quality
- follow existing architecture
- reuse helpers/dataclasses
- type hints
- deterministic
- Ruff clean
- no unrelated modifications

Run:
python -m ruff check `
  .\src\gridiron\market\economic_robustness.py `
  .\tests\test_market_economic_robustness.py

python -m pytest `
  .\tests\test_market_economic_robustness.py `
  .\tests\test_market_economic_validation.py `
  .\tests\test_market_robustness_research.py `
  .\tests\test_market_feature_residual_research.py `
  .\tests\test_market_untouched_validation.py

Finally print a concise Step 90G report containing every robustness slice with:
bets, win%, mean edge, profit, ROI.

Do not interpret the highest ROI slice as the preferred strategy.
The purpose is robustness, not optimization.

Do not commit or push anything yet.
