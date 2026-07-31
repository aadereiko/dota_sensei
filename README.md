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

`heroes` and `items` cache OpenDota's `/constants/*` (127 and 501 rows, static
within a patch, no API key). Heroes supply display names, icons, and the `roles`
tags that let the analysis rules tell a support from a core on an unparsed match.
Items are the reference page today and the lookup that will turn a purchase log's
numeric ids into "Black King Bar at 14:32". Both populate lazily on first use.

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

**Knowing the role without a parsed replay.** OpenDota only fills in `lane_role`,
the per-minute series and the purchase log for matches whose replay it has
*parsed* — in practice most of your recent games are not. That used to mean the
role-gated rules never ran at all on them.

`guess_role()` closes most of the gap by falling back to the hero's static role
tags from `/constants/heroes`, which are available for every match:

```python
lane_role in {1, 2}        -> "core"      # parsed replay, authoritative
lane_role in {3, 4}        -> "support"
"Support" in hero.roles and "Carry" not in hero.roles  -> "support"
"Carry" in hero.roles and "Support" not in hero.roles  -> "core"
otherwise                  -> None        # e.g. Windranger, tagged both
```

It's a weaker signal — someone can play a hero off-role — so heroes tagged both
Carry and Support resolve to `None` rather than being guessed at, and
`role_is_certain()` reports which source was used. In practice this took a real
unparsed Rubick game from two findings to three, and swapped "check your jungle
route" for advice a support can actually use.

**Forcing a parse.** You don't have to wait for one. `POST /api/matches/{id}/parse`
queues a parse with OpenDota — free, no key, no rate cost beyond the request —
and returns a job id. `GET /api/matches/{id}/parse/{job_id}` polls it, and once
the job lands it re-fetches the match, re-ingests it, and **re-runs the analysis**,
since a parse unlocks `lane_role` and the timeline and can make rules fire that
previously couldn't. The match page shows a "Request parse" button on any
unparsed game and polls in the background.

One wrinkle worth knowing: a finished job doesn't guarantee a parsed match — the
replay can simply be unavailable, especially for older games. So the poll treats
the re-fetched match as the source of truth, not the job status.

### Steam sign-in

Steam is an OpenID 2.0 *provider*, so there's no app to register and **no API key
to obtain** — you redirect to Steam, the user comes back with signed parameters,
and you ask Steam to confirm the signature:

```
browser → /api/auth/steam/login → steamcommunity.com → /api/auth/steam/callback
                                                              ↓
                                           POST back to Steam: check_authentication
                                                              ↓
                                        is_valid:true → session cookie → /?login=ok
```

All Steam returns is a SteamID64; `account_id` is its low 32 bits
(`steamid64 - 76561197960265728`), which is exactly what OpenDota wants. The
profile name and avatar come from OpenDota on first sign-in.

Two things that are easy to get wrong and are handled here:

- **`claimed_id` must be inside `openid.signed`.** A response can carry a
  perfectly valid signature that simply doesn't cover the identity fields, letting
  an attacker swap in any SteamID. `verify_callback` rejects those, and there's a
  test for exactly that case.
- **The callback and the app must share an origin.** A cookie set on
  `127.0.0.1:8273` is not sent by `localhost:5273` — different hosts. So
  `PUBLIC_BASE_URL` points at the Vite server, and the callback arrives through
  its `/api` proxy. Set it to your real origin in production.

The session is a signed (not encrypted) cookie holding only `account_id`, which
is public information anyway. `SameSite=Lax` is required rather than `Strict`,
since the Steam callback is a top-level cross-site redirect. Set
`DOTA_SENSEI_SECRET_KEY` to something real before deploying — the default is a
placeholder, and changing it signs everyone out.

Once signed in, `POST /api/sync` needs no body: the server reads the account from
the session. You can still pass an explicit `account_id` to look at anyone else.

### Public match data, and the way around it

OpenDota can only list your matches if **Dota 2 → Settings → Options → Advanced
Options → "Expose Public Match Data"** is enabled. With it off, `/api/sync`
returns `matches_seen: 0` — the profile still resolves, but OpenDota reports
`fh_unavailable: true` and has no history to give. Turning it on appears to start
your history from that point rather than backfilling, because OpenDota stores
each match as it's played and anonymises players who hadn't opted in.

`POST /api/matches/import` is the way around that. Matches are public even when
the players in them are anonymous, so a match id from your Dota client still
yields a full breakdown:

```jsonc
POST /api/matches/import  { "match_id": 8922669985 }

// If your account is visible in the match, done:
{ "match_id": ..., "resolved": true, "insights_created": 3 }

// If you were anonymised, we can't know which of the ten is you:
{ "match_id": ..., "resolved": false, "candidates": [ /* ten slots */ ] }

// so post again naming your slot:
POST /api/matches/import  { "match_id": 8922669985, "player_slot": 1 }
```

Claiming an anonymous slot writes your `account_id` onto that row, so the match
then behaves like any other — it shows up in your match list and feeds the
recurring-mistakes rollup. Claiming a slot that already belongs to a different
identified account is refused with a 409.

### The match page

`/matches/:matchId` shows the whole game:

- **Scoreboard** — both teams with levels, K/D/A, last hits, GPM, net worth, hero
  damage, and every player's six item slots, backpack and neutral item as icons.
- **Per-player detail** (click a hero) — lane efficiency, teamfight participation,
  APM, neutral kills, towers, buybacks, wards, and **item timings**: when each
  build item was actually bought.
- **Graphs** — per-minute gold and experience advantage.
- **Key moments** — first blood, every tower and barracks with the team credited,
  Roshan, aegis pickups, and the ancient falling.

Inventories and the scoreboard come from summary data, so they work on
**unparsed** matches. Everything else needs a parsed replay — hence the button.

Item timings filter the purchase log, which otherwise runs to ~40 entries of
tangoes and branches. The heuristic keeps anything `created` (built from
components) plus any non-consumable over 2000 gold — because `created` alone
misses Blink Dagger, which is bought outright and which OpenDota even tags as a
"component". The cost floor occasionally lets a raw Demon Edge through; that's
the accepted trade.

Three deliberate choices in the charts:

- **Gold and XP are separate charts, never one plot with two y-axes.** Two scales
  on one plot invent a correlation the data doesn't contain.
- **Radiant is blue, not the traditional green.** Green vs red measures ΔE 7.0
  under deuteranopia on this surface — inside the fail band. Blue vs red measures
  19.2. Position above/below the baseline carries the meaning regardless, so hue
  is redundant encoding rather than the only channel.
- **The domain fits the data but always includes zero**, with a minimum span so a
  game that stayed within a few hundred gold isn't stretched into a fake mountain
  range. A symmetric domain wasted half the canvas on the one-sided games that
  most matches actually are.

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
    main.tsx             router: / (matches), /heroes, /items
    App.tsx              recurring mistakes + match list + breakdown
    pages/
      HeroesPage.tsx     all heroes, filter by attribute and role
      ItemsPage.tsx      all items, filter by bucket and quality
    components/
      Layout.tsx         nav tabs + shared page furniture
```

Routing is `react-router-dom` with `BrowserRouter`, so deep links like `/heroes`
need the server to fall back to `index.html`. Vite's dev server does this out of
the box; a production static host needs it configured.

### API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | liveness + DB check |
| GET | `/api/config` | default account id for the UI |
| GET | `/api/heroes` | all 127 heroes |
| GET | `/api/items` | all 501 items |
| GET | `/api/auth/steam/login` | 302 to Steam |
| GET | `/api/auth/steam/callback` | verify, start session, 302 back to the app |
| GET | `/api/auth/me` | signed-in user (401 if not) |
| POST | `/api/auth/logout` | clear the session |
| POST | `/api/sync` | pull recent matches, run analysis |
| POST | `/api/matches/import` | analyse one match by id (works without public history) |
| GET | `/api/players/{id}` | profile |
| GET | `/api/players/{id}/matches` | match list with insight counts |
| GET | `/api/matches/{match_id}` | full scoreboard: both teams, inventories, graphs |
| POST | `/api/matches/{match_id}/parse` | ask OpenDota to parse the replay |
| GET | `/api/matches/{match_id}/parse/{job_id}` | poll it; re-ingests when it lands |
| GET | `/api/players/{id}/matches/{match_id}` | your line in a match + insights |
| GET | `/api/players/{id}/insights/recurring` | mistakes ranked by frequency |

## Getting started

```bash
make setup      # backend venv + npm install + .env from .env.example
make db         # postgres on 5473
make migrate    # create the schema
make backend    # API on 8273
make frontend   # UI on 5273
```

Then open http://localhost:5273 and **Sign in through Steam** — that's all the
setup there is; Steam OpenID needs no key or app registration. You can also paste
any account id to look at someone else's games without signing in.

An OpenDota API key is optional — without one you get 2000 calls/day at 60/min,
and each match detail is one call.

## Status

Architecture + working skeleton. Verified end to end against real Postgres and
the live OpenDota API: sync ingests real matches, the rules fire and persist,
re-running is idempotent, and the Vite proxy reaches the API. Backend tests and
ruff pass; the frontend typechecks and builds.

Steam sign-in works end to end at the protocol level: the login redirect carries
the right OpenID parameters, a forged callback is rejected by Steam's own
`check_authentication` and sets no cookie, a valid session resolves to the right
account, a tampered cookie 401s, and logout clears it. The one step not exercised
automatically is a human clicking through Steam's login page.

Next up:

- Findings can't reference each other, so 17 deaths and bottom-1% farm show up as
  two peer problems when the first plainly causes the second. Rules need a second
  pass over the whole finding set to rank and subordinate.
- Request a parse automatically for unparsed matches, then re-analyse
- Rules that read `timeline`: death clustering, item timing vs. benchmark,
  lane-phase outcome, gold-curve stalls
- Trends across matches rather than one game at a time
