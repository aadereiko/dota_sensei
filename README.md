# dota_sensei

Analyse my previous Dota 2 games and point out my mistakes.

## Idea

Pull match history and per-match detail for a Steam account, then surface concrete,
actionable feedback — not just raw stats. Things like:

- Heroes I keep losing on (and the ones I underplay)
- Farm efficiency vs. the benchmark for my role and bracket (GPM/XPM percentiles)
- Deaths that mattered: where and when I died, and what it cost
- Warding / vision contribution vs. expectation for the position
- Item timings that lag the benchmark (e.g. late core item on a carry)
- Patterns that separate my wins from my losses

## Stack

- **backend/** — Python. Fetches and analyses match data (OpenDota API), exposes it over HTTP.
- **frontend/** — React. Dashboard: match list, per-match breakdown, trends over time.

## Status

Scaffolding. Nothing implemented yet.
