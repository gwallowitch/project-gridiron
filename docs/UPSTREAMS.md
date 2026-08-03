# Upstream Evaluation Register

This register prevents unreviewed copy-and-paste reuse.

| Project | License | Decision | Approved use |
|---|---|---|---|
| nflverse/nflreadpy | MIT; dataset licenses vary | Adopt dependency | NFL data loading and caching |
| mattleonard16/nflalgorithm | MIT | Reference selectively | Backtest and operational design ideas after audit |
| gmalbert/nfl-predictions | No license located during review | Concepts only | Do not copy code |

## Reuse gate

Before adapting upstream code:

1. Record the repository, exact commit, file, and license.
2. Confirm that required data and modules are public.
3. Add characterization tests for the upstream behavior.
4. Check timestamps and feature construction for lookahead leakage.
5. Port the smallest coherent component.
6. Retain required copyright and license notices.
7. Compare the port with a simpler baseline.

## First audit finding

The current `mattleonard16/nflalgorithm` tests reference a root-level
`value_betting_engine.py`, while that file was not available on the default
branch during the 2026-08-02 review. Project Gridiron will therefore not depend
on that module or assume that the upstream application runs end to end.

