# Project Gridiron

Project Gridiron is an NFL analytics and decision-support platform. Its first
milestone is a reproducible data pipeline built on the open-source nflverse
ecosystem. It does not place wagers or promise profitable outcomes.

## Step 1: verify the data connection

Use Python 3.12 or 3.13 for the broadest data-science package compatibility.

```powershell
git clone <your-repository-url>
cd project-gridiron
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m gridiron.cli smoke-test --season 2025
python -m pytest
```

Before installing development dependencies, the core tests can also run with:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
```

The smoke test downloads the selected season's schedule through `nflreadpy`,
checks its schema, and prints a compact summary. It does not train a model.

## Design rules

- Prefer maintained open-source packages over custom scrapers.
- Preserve raw source data; transform into separate curated datasets.
- Use only information that existed before kickoff.
- Test chronologically; never randomly mix future games into training data.
- Require timestamped odds before calculating historical betting performance.
- Paper-test before considering real-money use.

## Initial layout

```text
project-gridiron/
|-- pyproject.toml
|-- README.md
|-- src/gridiron/
|   |-- cli.py
|   |-- data/nflverse.py
|   `-- validation/schedules.py
`-- tests/
    `-- test_schedule_validation.py
```

## Next increment

After the smoke test passes, Step 3 will persist schedules and play-by-play data
as Parquet files, add DuckDB metadata, and validate row counts and game IDs.

## Hybrid development policy

Project Gridiron uses maintained packages directly and selectively ports small,
audited ideas from compatible open-source repositories. Every imported or
adapted component must have a compatible license, attribution, focused tests,
and no unavailable private dependencies. See `docs/UPSTREAMS.md` and
`THIRD_PARTY_NOTICES.md`.

Version 0.2 adds a dependency-free market-math core for odds conversion,
two-outcome margin removal, expected value, and capped fractional Kelly sizing.
These functions support research and paper testing; they do not select bets.
