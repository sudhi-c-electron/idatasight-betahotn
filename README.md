# iDataSight

Belief-grounded data analysis. A [Reflex](https://reflex.dev) app implementing
the five-page loop from the iDataSight wireframes:
**Datasets → Beliefs → Analysis → Ledger → Memory**, with the Memory rail
always present. The backend functionality (ingestion, concept declarations,
analysis, ledger) is ported from the BetaThon dry runs and operates on the
real panels — the same data loaded into Snowflake `BETATHON`.

## Run

```sh
uv run reflex run
# open http://localhost:3000
```

## Data & sources

Real panels live under `data/warehouse/` (World Bank WDI education, fiscal,
trade, labor, inequality; Eurostat education finance — 29 countries,
2010–2023, pulled by the BetaThon dry runs). Two sources:

- **csv** (default) — the local mirror, no network needed.
- **snowflake** — `IDATASIGHT_SOURCE=snowflake` reads the same tables from
  `BETATHON.RAW.*` via `~/.snowflake/connections.toml`
  (`IDATASIGHT_SF_CONNECTION`, default `MN74135`, browser OAuth). Falls back
  to CSV on any failure.

"Refresh data" re-pulls live from the World Bank / Eurostat APIs, rewrites
the warehouse, and automatically re-runs the remembered belief (a re-run row
lands in the ledger).

`IDATASIGHT_DEMO=0` disables the wireframe-content fallback that covers
engine errors (with the real engine in place it is rarely reached).

## The loop, for real

- **Beliefs** — "Draft the grounding" distills a hypothesis into the
  dataset's formal Concept pack (definition · primary series · forbidden
  proxies · thresholds; seeds in `data/concepts/`, from the BetaThon
  ConsciousTwin records). "Ratify & remember" commits the next version to
  EverOS memory — a version is never overwritten, and an edited threshold
  really changes the verdicts.
- **Analysis** — verdicts per country under the recalled belief (latest
  non-null primary observation), proxy traps caught (e.g. Germany: 101%
  enrolled vs 64% complete), and the token receipt: grounded pack vs
  full-catalog context. On wdi this reproduces the BetaThon proof —
  7 disagreements, 70.8% ungrounded match, 1,399-token catalog.
- **Ledger** — every run appends a row to `data/store/ledger.json`; the
  chart is a live query over it. Row #1 is the dry run's cold episode.
- **Memory** — belief versions (meaning moved) and runs/refreshes (verdicts
  moved) merged into one timeline, kept visually apart.

## Memory substrate — EverOS

Beliefs live in the EverOS storage root (`EVEROS_ROOT`, default `~/.everos`),
speaking the storage-root layout natively (`idatasight/backend/everos.py`):

```
<root>/idatasight/<dataset_id>/
    agents/<user>/skills/skill_<concept>/
        SKILL.md                the canon of the latest ratified declaration
        references/v<N>.json    every version verbatim, append-only
    users/<user>/episodes/
        episode-<date>.md       every run booked as an entry-bracketed append
```

No server is required — the file canon suffices; an EverOS server started
over the same root indexes every unit. The markdown tree is the asset. Memory
is per-analyst (`IDATASIGHT_USER`, default `sudhi`) — two analysts can hold
different beliefs over the same data. Token-ledger rows stay in the
application (`data/store/ledger.json`); only the episode record is booked to
memory. On screen the vocabulary stays belief / remembered / recalled — the
substrate's name never appears in the UI.

## Test run

```sh
uv run python scripts/test_run.py            # includes a live Eurostat refresh
uv run python scripts/test_run.py --no-network
```

Writes `reports/TEST_RUN.md`. Last run: **all checks passed** — see that file
for the full verdicts, traps, receipts, and ledger produced from real data.

## Theming — one place

The entire look lives in `idatasight/theme.py` (colors, ramps, fonts,
spacing, radii, shadows, borders). No page or component hardcodes a style
value; edit that one file to retheme the app. It currently carries the
wireframes' "Modernist" system: Archivo, warm light-gray ground, `#ec3013`
accent, square corners.

## Backend seam — phase 2 (TAOpy)

The UI never talks to the backend directly. Every action builds a typed
message (`idatasight/backend/messages.py`) and sends it through one function:
`idatasight/backend/hooks.py :: dispatch(msg)`, which routes to
`backend/engine.py`. In phase 2 the engine handlers become TAOpy actor bodies
(`dataset-actor`, `belief-actor`, `analysis-actor`, `ledger-actor` — map
documented in `hooks.py`); the messages become `tao.Event` value objects.
Nothing in the UI changes.

## Layout

```
idatasight/
├─ idatasight.py      app entry — global style + page registration
├─ theme.py           ← the one place the look is defined
├─ config.py          DEMO_MODE flag
├─ models.py          view models + dispatch reply contracts
├─ state.py           AppState — all handlers go through dispatch()
├─ backend/
│  ├─ messages.py     actor-message vocabulary (phase-2 tao.Events)
│  ├─ hooks.py        dispatch() — THE seam
│  ├─ engine.py       message router → the handlers below
│  ├─ everos.py       EverOS memory substrate (storage-root canon)
│  ├─ warehouse.py    dataset registry + CSV/Snowflake readers
│  ├─ concepts.py     draft · ratify · remember/recall via EverOS · history
│  ├─ scoring.py      verdicts · traps · token receipt (BetaThon port)
│  ├─ ledger_store.py append-only run log → chart/tiles
│  ├─ ingest.py       live World Bank / Eurostat refresh
│  └─ demo.py         wireframe demo content (error fallback)
├─ components/        Modernist primitives + shell (nav, memory rail)
├─ pages/             datasets · beliefs · analysis · ledger · memory
data/
├─ warehouse/         real panels (CSV mirror of Snowflake BETATHON)
├─ concepts/          formal Concept seeds (BetaThon records)
└─ store/             app-owned token ledger (beliefs live in EVEROS_ROOT)
scripts/test_run.py   end-to-end engine test → reports/TEST_RUN.md
```
