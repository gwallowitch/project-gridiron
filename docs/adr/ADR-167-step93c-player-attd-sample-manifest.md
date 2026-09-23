# ADR-167: Step 93C player ATTD sample manifest

## Status

Accepted as a frozen, outcome-free, pre-acquisition sample authority.

## Purpose and boundary

Step 93B froze a deterministic six-request validation protocol but could not
materialize it because the approved local Step 92F schedule covered 2021, 2023,
and 2025 rather than the required 2023, 2024, and 2025. Step 93C resolves only
that schedule-authority gap and freezes the exact sample.

**STEP 93C MAKES ZERO PROVIDER REQUESTS.**

**STEP 93C CONSUMES ZERO API CREDITS.**

**STEP 93C DOES NOT FIT A PLAYER-TD MODEL.**

**STEP 93C DOES NOT PERFORM BULK HISTORICAL ACQUISITION.**

**STEP 93C DOES NOT USE TD OUTCOMES TO SELECT GAMES.**

**STEP 93C DOES NOT MODIFY THE FROZEN SPREAD LANE.**

**STEP 93C DOES NOT MODIFY THE FROZEN MONEYLINE CANDIDATE.**

## Approved schedule authority and provenance

Step 93C reuses the public nflverse schedule-release authority and governance
pattern approved in Step 92F. The release/tag identity is unchanged, while the
rolling release asset has been updated since Step 92F.

- Provider: `nflverse/nflverse-data`
- Release: `https://github.com/nflverse/nflverse-data/releases/tag/schedules`
- Release ID: `251386473`
- Tag commit: `ab1331c85fd222ce953fe61363b099c0629de0a1`
- Asset: `games.parquet`
- Asset ID: `584596352`
- Asset created/updated: `2026-09-23T21:16:18Z`
- Asset size: `521022` bytes
- Asset SHA-256:
  `edde2cff36388e86dfe0f1087cf9d1735c2d95f46079f55fbc7825956b877530`
- Retrieval: `2026-09-23T21:33:18.528471Z`

The raw asset contained fields outside the schedule contract. It was verified
in temporary storage, projected through a strict allowlist, and deleted. It is
not retained in the repository.

## Outcome-free transformation

Only the following fields are committed:

- `game_id`
- `season`
- `season_type`
- `week`
- `home_team`
- `away_team`
- `kickoff_at`

The derived artifact contains only regular-season games from 2023, 2024, and
2025: exactly 272 games per season and 816 total. Scores, winners, margins,
spreads, moneylines, totals, touchdowns, player data, injuries, results,
profit, and ROI are excluded before sample selection.

Derived schedule SHA-256:
`3eafad9f2a04b03092d6adee72d2d20990b6438c6b088bda2b8b75a6ad741bd4`

## Deterministic game selection

For each frozen season, regular-season games are ordered by UTC kickoff and
then canonical game ID. The first game is selected without inspecting player,
injury, sportsbook, price, or outcome information.

| Season | Canonical game | Matchup | Kickoff UTC |
|---|---|---|---|
| 2023 | `2023_01_DET_KC` | DET @ KC | `2023-09-08T00:20:00Z` |
| 2024 | `2024_01_BAL_KC` | BAL @ KC | `2024-09-06T00:20:00Z` |
| 2025 | `2025_01_DAL_PHI` | DAL @ PHI | `2025-09-05T00:20:00Z` |

## Exact six sample items

| Season | Game | Snapshot | Requested UTC | Item SHA-256 |
|---|---|---|---|---|
| 2023 | `2023_01_DET_KC` | T12H | `2023-09-07T12:20:00Z` | `c3c994a28778057314276f2994e4006b373d2f7cf930bf60a7b6c0d0d1ad3327` |
| 2023 | `2023_01_DET_KC` | T1H | `2023-09-07T23:20:00Z` | `91fb7a851b96d6ca279ab7673ab67886913d15b84d7d04cffd54e9d857b042a9` |
| 2024 | `2024_01_BAL_KC` | T12H | `2024-09-05T12:20:00Z` | `9d73db0e6d70d777e967f61777bb1af0fd09331bf9226e37c1c31c5a58c1ff06` |
| 2024 | `2024_01_BAL_KC` | T1H | `2024-09-05T23:20:00Z` | `b746d7c8a662e40cd6a1d185e97915152a536b168b08bac6754fa7729902f30e` |
| 2025 | `2025_01_DAL_PHI` | T12H | `2025-09-04T12:20:00Z` | `1522d82c4e02deaa2c4cc6fd0cbf8e23da64465a335be5eb91c99ccbd043e40c` |
| 2025 | `2025_01_DAL_PHI` | T1H | `2025-09-04T23:20:00Z` | `7e94f087fa32703ea381415e5f02e0f3dac8d8fe1be0114a9550ac7bd5b04af1` |

Every item freezes sport `americanfootball_nfl`, market
`player_anytime_td`, books `draftkings`, `fanduel`, and `betmgm`, region `us`,
American odds, and purpose `SCHEMA_AND_COVERAGE_VALIDATION`.

Manifest SHA-256:
`b120ac96101f01846906a66eab1987cfa57dbfbbd742e58384fb1f5f4edda927`

## Request and credit boundary

The manifest contains exactly six future requests. At the frozen planning
assumption of 10 credits per historical event/market/region snapshot, the
estimated ceiling is 60 credits. This is not a billing guarantee.

No request was executed and no credit was consumed. The manifest does not
answer book coverage, board completeness, Yes/No structure, player identity,
timestamps, suspended/removed-player behavior, schema differences, or
retention questions. It does not authorize bulk acquisition.

The next action is human review of this exact manifest before any paid sample
request. No provider request follows automatically from this ADR.
