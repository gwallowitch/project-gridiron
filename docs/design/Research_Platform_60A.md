# Research Platform 60A

## Command

```powershell
python ship.py research --profile modern
```

## Inputs

For every selected season, the following persisted files must exist:

- schedule
- PGR
- rest features

The command also loads the existing experiment matrix from
`config/experiments.toml`.

## Outputs

- console execution report
- `data/reports/research/research_registry.json`

## Scope boundary

60A executes and records all season-experiment combinations. Aggregate
rankings, statistical testing, and promotion recommendations are deferred
to 60B–60D.
