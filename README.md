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

## Ports

Chosen so nothing collides with the other projects on this machine (opik uses
3003/3333/5174/8000/8080/8081/8888/9080/…, psy/computational-learning uses
5211/8321/5433). Everything here lives in the **`*273` family**:

| Service | Port |
| --- | --- |
| Frontend (Vite dev server) | **5273** |
| Backend API (FastAPI/uvicorn) | **8273** |
| Postgres (host → container 5432) | **5473** |

Vite uses `strictPort`, so a clash fails loudly instead of silently drifting to 5274.

## Architecture

```
                 OpenDota API
                      │  httpx
                      ▼
        ┌──────────────────────────────┐
        │ services/opendota.py         │  API client
        │ services/ingest.py           │  fetch → upsert → analyse
        └──────────────┬───────────────┘
                       │
             ┌─────────▼──────────┐        ┌───────────────────────┐
             │ Postgres (5473)    │        │ analysis/             │
             │  players           │        │  base.py   registry   │
             │  matches           │◀──────▶│  rules.py  detectors  │
             │  match_players     │        └───────────────────────┘
             │  insights          │         pure fns: MatchPlayer → Finding
             └─────────┬──────────┘
                       │ SQLAlchemy 2.0 async
             ┌─────────▼──────────┐
             │ api.py  (FastAPI)  │  :8273
             └─────────┬──────────┘
                       │ /api/* proxied by Vite
             ┌─────────▼──────────┐
             │ React 19 + TS      │  :5273
             │ TanStack Query     │
             │ Tailwind v4        │
             └────────────────────┘
```

### Data model

`match_players` is the grain everything hangs off — one row per (match, player),
holding the stat line plus JSONB blobs for the per-minute series (`timeline`),
OpenDota's hero percentile `benchmarks`, and `item_timings`. `insights` are
materialised findings: one row per (performance, rule), so "which mistakes do I
keep making" is a single `GROUP BY rule_key`.

### Analysis rules

A rule is a pure function `MatchPlayer → Finding | None`, registered by decorator:

```python
@rule("death_count_high")
def death_count_high(p: MatchPlayer) -> Finding | None:
    ...
```

No DB, no network — so each one unit-tests by constructing a `MatchPlayer`.
Four starters ship: `farm_below_benchmark`, `last_hit_efficiency`,
`death_count_high`, `vision_deficit`. Adding a rule is one function plus one test.

**Parsed vs. unparsed matches.** OpenDota only fills in `lane_role`, the
per-minute series and the purchase log for matches whose replay it has *parsed* —
in practice most of your recent games are not. Rules that gate on role therefore
can't run on them, which is why `matches.is_parsed` is stored and surfaced in the
API and UI: a match with no findings is genuinely clean, or simply unparsed, and
you should be able to tell which. `farm_below_benchmark` deliberately has no role
gate — OpenDota's benchmarks are per-hero and so already role-normalised.
`OpenDotaClient.request_parse()` asks for a parse; wiring it into the sync flow is
the obvious next step.

### Layout

```
backend/
  app/
    config.py            pydantic-settings, DOTA_SENSEI_* env vars
    db.py                async engine, session dependency
    models.py            SQLAlchemy 2.0 models
    schemas.py           pydantic DTOs (the wire format)
    api.py               FastAPI routes
    cli.py               dota-sensei serve | sync | rules
    services/
      opendota.py        async OpenDota client
      ingest.py          fetch → upsert → run rules → persist insights
    analysis/
      base.py            Finding, @rule registry, evaluate_all
      rules.py           the mistake detectors
  alembic/               async migration env
  tests/
frontend/
  src/
    api.ts               typed fetch wrappers
    types.ts             mirrors schemas.py
    App.tsx              recurring mistakes + match list + breakdown
    components/
```

### API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | liveness + DB check |
| GET | `/api/config` | default account id for the UI |
| POST | `/api/sync` | pull recent matches, run analysis |
| GET | `/api/players/{id}` | profile |
| GET | `/api/players/{id}/matches` | match list with insight counts |
| GET | `/api/players/{id}/matches/{match_id}` | full breakdown + insights |
| GET | `/api/players/{id}/insights/recurring` | mistakes ranked by frequency |

## Getting started

```bash
make setup      # backend venv + npm install + .env from .env.example
make db         # postgres on 5473
make migrate    # create the schema
make backend    # API on 8273
make frontend   # UI on 5273
```

Then open http://localhost:5273 and enter your account id (the number in your
Dotabuff / OpenDota profile URL), or set `DOTA_SENSEI_DEFAULT_ACCOUNT_ID` in
`.env` to have it preloaded.

An OpenDota API key is optional — without one you get 2000 calls/day at 60/min,
and each match detail is one call.

## Status

Architecture + working skeleton. Verified end to end against real Postgres and
the live OpenDota API: sync ingests real matches, the rules fire and persist,
re-running is idempotent, and the Vite proxy reaches the API. Backend tests and
ruff pass; the frontend typechecks and builds.

Next up:

- Hero names and icons from `/heroStats` (the UI shows raw hero ids today)
- Request a parse automatically for unparsed matches, then re-analyse
- Rules that read `timeline`: death clustering, item timing vs. benchmark,
  lane-phase outcome, gold-curve stalls
- Trends across matches rather than one game at a time
