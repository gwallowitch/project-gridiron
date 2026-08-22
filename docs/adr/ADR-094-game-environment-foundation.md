# ADR-094 — Game Environment Foundation

## Status
Accepted for Step 82A.

## Purpose
Step 82 begins a new orthogonal research family after Step 81 rejected ordinary
travel weighting.

Step 82A creates historical game-environment features from fields already
available on the schedule artifact.

## Features
- temperature in Fahrenheit;
- wind speed in mph;
- weather text;
- roof / indoor state;
- surface and stadium metadata;
- rain / precipitation flag;
- snow / wintry flag;
- extreme cold flag (<= 32 F);
- extreme heat flag (>= 85 F);
- high wind flag (>= 15 mph);
- adverse-weather count and boolean.

## Data contract
82A does not fetch live forecasts. It is a historical research foundation.

Observed historical game conditions may be useful for feature discovery, but
they are not automatically production-safe because an exact observed weather
condition is not known before kickoff.

Before any environment feature is promoted for live prediction, a later step
must define an explicit prediction-time weather contract using only information
available at the model's decision timestamp.

## Baseline
The promoted six-weight baseline remains untouched.
