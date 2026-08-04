# Project Gridiron Benchmark Framework

## Purpose

The benchmark framework measures the health and stability of PGR datasets. It provides evidence for future model changes and establishes a repeatable evaluation interface.

## Command

```powershell
python ship.py benchmark --season 2025
```

## Version 1 metrics

- League average and median
- Population standard deviation
- Minimum, maximum, and spread
- Average absolute weekly movement
- Maximum absolute weekly movement
- Number of movement observations
- Evaluation runtime

## Scope

Version 1 does not measure win accuracy, calibration, point-margin error, or betting performance. Those metrics require the future prediction and outcome-evaluation layers.
