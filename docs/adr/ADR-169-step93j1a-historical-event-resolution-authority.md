# ADR-169: Step 93J.1A bounded historical event-ID resolution authority

## Status

Pending independent review. Discovery execution is disabled.

## Context

Step 93J.2 correctly stopped before implementation because each historical
Player Anytime TD event-odds request requires a provider event ID while all six
items in the frozen Step 93C manifest contain `provider_event_id: null`. The
provider documents a separate paid-plan historical-events endpoint for finding
those IDs. Treating discovery as an implicit prerequisite to the six requests
would have exceeded the reviewed Step 93J.1 authority.

The provider endpoint is
`GET /v4/historical/sports/{sport}/events?apiKey={apiKey}&date={date}`. A
historical response lists events that had odds at the selected snapshot and
includes `id`, `commence_time`, `home_team`, and `away_team`. The documented
cost is one usage credit when events are found. The requested date resolves to
the closest provider snapshot at or before that value.

## Decision

Define a second, non-production authority type,
`HISTORICAL_PLAYER_ATTD_EVENT_RESOLUTION_V1`. It permits only three future
historical-events requests: one for each frozen 2023, 2024, and 2025 game. It
does not authorize an odds market or alter the six-request J.1 authority.

Each discovery date is the corresponding frozen T12H request timestamp:

- `2023_01_DET_KC`: `2023-09-07T12:20:00Z`
- `2024_01_BAL_KC`: `2024-09-05T12:20:00Z`
- `2025_01_DAL_PHI`: `2025-09-04T12:20:00Z`

Three calls are minimal because the provider returns events visible at one
historical snapshot and the frozen games occur in three different years. The
authority permits no alternate dates, ranges, retries, probing, pagination,
current-events requests, or season crawling.

Future resolution must find exactly one event with the exact sport, frozen
kickoff, and exact provider home/away names bound in the authority. Zero or
multiple matches, reversed teams, or a kickoff mismatch fail closed. Fuzzy or
closest-game matching is prohibited.

The deterministic authority artifact is
`data/reference/player_td_sample_v1/step93j1a_historical_event_resolution_authority.json`.
It binds the frozen Step 93C manifest hash and Step 93J.1 authority hash. Its
`execution_enabled` value remains false. This step neither source-pins the new
hash nor implements provider transport; both require later independent review.

## Future evidence contract

Future exact discovery bytes and metadata belong under
`data/research/player_td_validation/step93c_sample/event_resolution/`. The
canonical result belongs at
`data/research/player_td_validation/step93c_sample/provider_event_resolution.json`.
It must bind both authorities, the manifest, frozen game identity, discovery
date, provider identity fields, raw SHA-256, and acquisition time without
modifying Step 93C.

Writes must be append-once and conflict-safe. Different existing bytes,
partial pairs, malformed evidence, and path or symlink substitution fail
closed. Exact replay may be idempotent only when all retained evidence agrees.

## Budgets and boundaries

The scopes stay separate:

- Event resolution: at most 3 transport calls and, when nonempty, 3 documented
  usage credits.
- Player ATTD market acquisition: exactly the separately governed 6 requests,
  with the existing planning estimate of at most 60 credits.
- Combined planning ceiling: 9 provider calls and 63 credits.

A discovery call can never become a market request. The future resolver may
read `GRIDIRON_ODDS_API_KEY` only during an explicitly authorized execution and
must never retain or expose it. Step 93J.1A reads no credential, contacts no
provider, creates no execution state, and creates no research evidence.

Step 93C and Step 93J.1 remain immutable. Actual discovery and market
acquisition each require separately reviewed activation.
