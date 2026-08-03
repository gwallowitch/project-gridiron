# Project Gridiron

**Professional Football Analytics Platform**

Project Gridiron is an open, test-driven NFL analytics platform focused on reproducible data engineering, transparent rating models, and predictive analytics. The project emphasizes modular pipelines, validated datasets, and explainable algorithms rather than black-box predictions.

> **Current status:** Alpha 0.1 (Active Development)

## Current Capabilities

- Automated NFL schedule ingestion
- Automated play-by-play ingestion
- Curated team-game feature store
- Team metrics engine
- Metric normalization (league average = 100)
- Team rating engine
- Ratings pipeline
- Season orchestration pipeline
- DuckDB metadata catalog
- Mission Control (`ship.py`)
- Comprehensive automated test suite (currently 76 passing tests)

## Architecture

```text
NFLVerse
    ↓
Schedule Pipeline
    ↓
Play-by-Play Pipeline
    ↓
Team Game Feature Store
    ↓
Team Metrics
    ↓
Normalization
    ↓
Team Ratings
    ↓
Power Ratings (In Development)
```

## Technology

- Python 3.13
- Polars
- DuckDB
- Pytest
- Ruff
- nflverse / nflreadpy

## Quick Start

```powershell
git clone https://github.com/gwallowitch/project-gridiron.git
cd project-gridiron
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
python ship.py
```

## Engineering Principles

- Reproducible pipelines
- Modular architecture
- Test-driven development
- Explainable ratings
- Preserve raw data and build curated datasets
- Never use information unavailable before kickoff

## Roadmap

### Alpha 0.2
- Power Ratings
- Strength of Schedule
- Opponent Adjustments

### Alpha 0.3
- Prediction Engine
- Weekly Ratings

### Beta
- Monte Carlo Simulation
- Dashboard
- Reporting

### Version 1.0
- End-to-end analytics platform
- One-command workflow
- Stable public release
