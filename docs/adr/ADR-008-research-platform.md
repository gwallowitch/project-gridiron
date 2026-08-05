# ADR-008: Multi-Season Research Platform

## Status

Accepted

## Context

Single-season experiments can overfit to one schedule, roster environment,
or scoring distribution. Project Gridiron needs a repeatable way to execute
the same experiment matrix across multiple seasons.

## Decision

Add a research layer that:

- loads named season profiles from TOML;
- excludes anomalous seasons explicitly;
- runs the existing experiment framework once per season;
- records reproducibility metadata;
- persists complete run history to a JSON registry.

Milestone 60A intentionally does not aggregate metrics or recommend model
promotion. Those capabilities belong to later research milestones.

## Season policy

- `modern`: 2022–2025
- `transition`: 2021
- `historical`: 2010–2019
- excluded by default: 2020
