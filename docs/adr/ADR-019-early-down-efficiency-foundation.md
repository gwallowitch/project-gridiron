# ADR-019: Early-Down Efficiency Foundation
64A builds pregame rolling first/second-down EPA, success, pass/rush EPA and explosive-play metrics from nflverse play-by-play.
For week N, only weeks strictly less than N in the same season are eligible.
64A is standalone and is not wired into research scoring or production predictions.
Opponent adjustment is deferred until the raw rolling artifacts are validated.
