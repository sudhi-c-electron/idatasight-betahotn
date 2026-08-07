# iDataSight — engine test run on real data

**Generated:** 2026-08-07T16:18:35  
**Panels:** BetaThon dry-run extracts (World Bank WDI + Eurostat), local CSV mirror of Snowflake `BETATHON`.

## 1 · Ingestion

| Dataset | Source | Panel | Beliefs watching |
|---------|--------|-------|------------------|
| Education panel | World Bank WDI | 29 countries · 2010–2023 · 4,872 rows (refreshed 2026-08-07) | 5 |
| Fiscal | World Bank | 29 countries · 2010–2023 · 2,436 rows (refreshed Aug 2026) | 1 |
| Trade | World Bank | 29 countries · 2010–2023 · 2,436 rows (refreshed Aug 2026) | 2 |
| Labor | World Bank | 29 countries · 2010–2023 · 2,436 rows (refreshed Aug 2026) | 2 |
| Inequality | World Bank | 29 countries · 2010–2023 · 2,436 rows (refreshed Aug 2026) | 1 |
| EU edu finance | Eurostat | 20 countries · 2012–2022 · 3,205 rows (refreshed 2026-08-07) | 1 |

- ✅ six datasets registered
- ✅ education panel matches the dry-run extract — 29 countries · 2010–2023 · 4,872 rows
- ✅ wdi columns described in plain language

## 2 · Concept declaration (Beliefs)

Drafted grounding pack:

- **Definition** — success = completing secondary school, not being in it
- **Primary** — SE.SEC.CMPT.LO.ZS
- **Forbidden** — enrollment — counts repeaters · spend — effort, not result · GDP — wealth, not schooling · tertiary enrollment — access, not completion
- **Threshold** — High ≥ 90% · Moderate ≥ 75%

- ✅ draft carries the four pack fields
- ✅ ratified as a new version (never overwrites) — v2 · Aug 7, 2026
- ✅ tightened threshold moved verdicts on the same data — Success verdicts 17 → 13 (High ≥ 90 → 95)
- ✅ reopening drafts from the remembered belief, not the seed — High ≥ 95% · Moderate ≥ 75%

## 3 · Analysis — verdicts · traps · receipt

### wdi — Spending ≠ completion · v1 (v1 run)

- Verdicts: **29** countries — 24 evaluable, 5 outside envelope
- 7 of 24 verdicts differ from the unguided blend (70.8% match) — your belief changed the answer
- Trap — **Colombia**: enrollment 102% vs completion 83%; unguided read “success”, belief says **not yet**
- Trap — **Germany**: enrollment 101% vs completion 64%; unguided read “success”, belief says **not yet**
- Receipt: grounded **572 tok · 29 series** vs ungrounded **1399 · 86**

- ✅ disagreements match the BetaThon dry-run proof — 7 vs proof 7
- ✅ ungrounded receipt matches the dry-run proof — 1399 tok · 86 series
- ✅ grounded package within 5% of the dry-run 585 — 572 tok
- ✅ the Germany enrollment-vs-completion trap is caught — 101% enrolled, 64% complete

### fiscal — Fiscal effort · v1

- Verdicts: 29 entities — 25 evaluable, 4 outside envelope
- 20 of 25 verdicts differ from the unguided blend (20% match) — your belief changed the answer
- Receipt: grounded 190 tok · 29 series vs ungrounded 789 · 142

- ✅ fiscal: grounding shrinks context and series
### trade — Export orientation · v1

- Verdicts: 29 entities — 28 evaluable, 1 outside envelope
- 21 of 28 verdicts differ from the unguided blend (25% match) — your belief changed the answer
- Receipt: grounded 184 tok · 29 series vs ungrounded 732 · 171

- ✅ trade: grounding shrinks context and series
## 4 · Live refresh — Eurostat

> skipped (--no-network)

## 5 · Ledger — every run appended a row

| Row | Tokens (with memory) | Tokens (without) |
|-----|----------------------|------------------|
| ep 1 | 1,399 | 1,399 |
| ep 2 | 572 | 1,399 |
| ep 3 | 540 | 1,399 |
| ep 4 | 190 | 789 |
| ep 5 | 184 | 732 |

- **run 2** — pack pays for itself
- **−68%** — every run after
- **2,885** — cumulative vs 5,718

- ✅ ledger accumulated the session's runs — 5 rows
- ✅ the first-recall cliff is visible (ep1 cold → ep2 recalled) — 1,399 → 572

## 6 · Memory — two histories, kept apart

**Spending ≠ completion** — Edit → v3

- ○ **Row #3 — run · 24 verdicts**  — recalled v2 · 540 tokens · 100% vs declared truth
- ○ **Row #2 — run · 24 verdicts**  — recalled v1 · 572 tokens · 100% vs declared truth
- ○ **Row #1 — cold run · 24 verdicts**  — 1,399 tokens · 70.8% vs declared truth
- ● **v2 — revised** Aug 2026 — Forbidden: enrollment — counts repeaters · spend — effort, not result · GDP — wealth, not schooling · tertiary enrollment — access, not completion → enrollment — counts repeaters · spend — effort, not result · GDP — wealth, not schooling · Threshold: High ≥ 90% · Moderate ≥ 75% → High ≥ 95% · Moderate ≥ 75%
- ● **v1 — declared** Aug 2026 — “Secondary completion is the attainment of a recognized lower- or upper-secondary school-leaving milestone by t”

> Same data, two beliefs — the “effort” belief calls 3 countries a success that “completion” does not (Colombia, Germany, South Africa). Both provably right, each under its own belief.

- ✅ timeline separates belief changes from data runs — 2 belief · 3 data events

## 7 · Memory substrate — remembered and recalled

Storage root (scratch): `/Users/cworks/PLATFORM/APPLICATIONS/iDataSight/data/store/test_everos` — pack plane holds ['v1.json', 'v2.json'], episodes plane holds 2 booked runs.

- ✅ belief versions remembered append-only in the pack plane — v1.json, v2.json
- ✅ SKILL.md is the canon of the latest ratified declaration
- ✅ recall returns the remembered v2 with its parsed thresholds — v2 · high ≥ 95
- ✅ every wdi run is booked as an episode in memory — episodes [2, 3] vs ledger rows [2, 3]

## Verdict

**ALL CHECKS PASSED** — ingestion, concept declaration, and analysis run on the real panels and reproduce the BetaThon dry-run proof.
