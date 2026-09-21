# ADR-164: Step 92F historical schedule authority and final manifest

## Status

Accepted as an outcome-free, pre-acquisition reference authority.

## Source and provenance

The local repository did not contain a complete historical schedule authority
for 2021, 2023, and 2025. Step 92F therefore used the public nflverse
`nflverse-data` schedules release, matching the repository's established
`nflreadpy.load_schedules` source and team/game identity convention.

- Release: `https://github.com/nflverse/nflverse-data/releases/tag/schedules`
- Release ID: `251386473`
- Release tag commit: `ab1331c85fd222ce953fe61363b099c0629de0a1`
- Asset: `games.parquet`, GitHub asset ID `579741037`
- Asset SHA-256: `660fd3ee7cf75417358bae421c0471459a43005cbff015129ec1da625bf12fb4`
- Asset size: 520,852 bytes
- Asset update: `2026-09-21T19:46:25Z`
- Retrieval: `2026-09-21T20:25:38Z`

The upstream contains results and betting columns. To prevent outcome leakage,
the raw asset was verified in a temporary directory but is not retained in the
repository. Its immutable asset identity, commit, metadata, and SHA-256 are
retained. The deterministic transformer projects only `game_id`, `season`,
`season_type`, `week`, `home_team`, `away_team`, and UTC `kickoff_at`.

Kickoff values use the same documented nflverse convention already employed by
Project Gridiron: `gameday` plus `gametime` in `America/New_York`, converted to
UTC. `game_type=REG` remains REG and `game_type=WC` remains WC. Canonical game
IDs retain the existing nflverse-compatible form `YYYY_WW_AWAY_HOME`.

All 21 selected games have `location=Home` in the pinned source; none is an
international or neutral-site game. The selected seasons use contemporary team
abbreviations without a relocation alias. The pinned asset supplies the final
listed kickoff but no revision history, so Step 92F makes no claim that an
earlier postponement or rescheduling never occurred.

## Frozen artifacts

The derived schedule contains 158 eligible pool rows and has SHA-256:

`db263a3df39bd1d72a3882168328b833fbc1327f61d3a2e1eac991f3bfdf1128`

The frozen Step 92E selector produced 21 games: 18 regular-season games and
three Wild Card games. It generated five targets per game, exactly 105 request
items: 35 per season, 21 per target, and five per game.

The final manifest SHA-256 is:

`e45976ed4768335095d3f6298a039c40a9ec1edb82361dddc11064e9ed8d464d`

At the reporting assumption of 10 credits per request, the exact estimate is
1,050 credits. This is not a plan purchase or permanent pricing assertion.

The human-readable manifest review lists only schedule identity and the five
target timestamps for each selected game. It contains no scores, result,
margin, ATS, spread, price, profit, ROI, edge, or model output.

## Boundary

**STEP 92F DOES NOT AUTHORIZE HISTORICAL ODDS ACQUISITION.**

**STEP 92F DOES NOT AUTHORIZE MODEL FITTING.**

**STEP 92F DOES NOT AUTHORIZE PERFORMANCE ANALYSIS.**

**STEP 92F DOES NOT CREATE FORMAL PROSPECTIVE EVIDENCE.**

No Odds API key, provider request, sportsbook quote, 2026 outcome, cloud
service, or operational evidence was accessed or changed. The next action must
be explicit human authorization of this exact manifest and its estimated 1,050
historical-provider credits.
