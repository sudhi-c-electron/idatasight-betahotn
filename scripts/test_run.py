#!/usr/bin/env python3
"""End-to-end test run of the iDataSight engine on the real BetaThon panels.

Exercises every message in the backend protocol and writes
reports/TEST_RUN.md with the actual outputs:

  1. Ingestion   — dataset registry + columns from the warehouse; a live
                   Eurostat refresh (network) that re-runs the belief.
  2. Declaration — draft the grounding, ratify a revised v2 with a tightened
                   threshold, show that verdicts move.
  3. Analysis    — verdicts, traps, and the token receipt on wdi + fiscal +
                   trade, checked against the BetaThon dry-run proof.
  4. Ledger      — the appended rows and computed tiles.
  5. Memory      — the two-history timeline for the wdi belief.
  6. Substrate   — the EverOS storage root: append-only pack plane, SKILL.md
                   canon, recall round-trip, runs booked as episodes (in a
                   scratch root under data/store — the analyst's real memory
                   at EVEROS_ROOT/~/.everos is never touched by tests).

Run:  uv run python scripts/test_run.py [--no-network]
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Deterministic sandbox: the test owns data/store (app ledger) and a scratch
# EverOS root inside it — the analyst's real memory (~/.everos) is never
# touched by tests.
shutil.rmtree(ROOT / "data" / "store", ignore_errors=True)
os.environ["EVEROS_ROOT"] = str(ROOT / "data" / "store" / "test_everos")

from idatasight.backend import concepts, engine, ledger_store  # noqa: E402
from idatasight.backend import messages as m  # noqa: E402
from idatasight.backend.warehouse import WAREHOUSE  # noqa: E402
from idatasight.config import USER  # noqa: E402

REPORT = ROOT / "reports" / "TEST_RUN.md"

NETWORK = "--no-network" not in sys.argv


def main() -> int:
    lines: list[str] = [
        "# iDataSight — engine test run on real data",
        "",
        f"**Generated:** {datetime.now().isoformat(timespec='seconds')}  ",
        "**Panels:** BetaThon dry-run extracts (World Bank WDI + Eurostat), "
        "local CSV mirror of Snowflake `BETATHON`.",
        "",
    ]
    failures: list[str] = []

    def check(name: str, ok: bool, detail: str = ""):
        mark = "✅" if ok else "❌"
        lines.append(f"- {mark} {name}" + (f" — {detail}" if detail else ""))
        if not ok:
            failures.append(name)

    # ── 1 · Ingestion ──────────────────────────────────────────────────────
    lines += ["## 1 · Ingestion", ""]
    datasets = engine.handle(m.ListDatasets())
    lines.append("| Dataset | Source | Panel | Beliefs watching |")
    lines.append("|---------|--------|-------|------------------|")
    for d in datasets:
        lines.append(
            f"| {d.name} | {d.source} | {d.summary} ({d.refreshed}) | {d.beliefs_attached} |"
        )
    lines.append("")
    check("six datasets registered", len(datasets) == 6)
    wdi = next(d for d in datasets if d.id == "wdi")
    check(
        "education panel matches the dry-run extract",
        "4,872 rows" in wdi.summary and "29 countries" in wdi.summary,
        wdi.summary,
    )

    cols = engine.handle(m.FetchColumns(dataset_id="wdi"))
    check("wdi columns described in plain language", len(cols) == 12)
    lines.append("")

    # ── 2 · Concept declaration ────────────────────────────────────────────
    lines += ["## 2 · Concept declaration (Beliefs)", ""]
    draft = engine.handle(
        m.DraftGrounding(
            hypothesis=(
                "Government spending does not equal secondary completion. "
                "Effort is not outcome."
            ),
            dataset_id="wdi",
        )
    )
    lines.append("Drafted grounding pack:")
    lines.append("")
    for f in draft.fields:
        lines.append(f"- **{f.key}** — {f.value}")
    lines.append("")
    check("draft carries the four pack fields", len(draft.fields) == 4)

    v1_result = engine.handle(m.RunAnalysis(dataset_id="wdi", belief_id=""))
    v1_success = sum(1 for v in v1_result.verdicts if v.verdict == "Success")

    ratified = engine.handle(
        m.RatifyBelief(
            dataset_id="wdi",
            statement=(
                "Government spending does not equal secondary completion. "
                "Effort is not outcome."
            ),
            fields={
                "Definition": "success = completing secondary school, not being in it",
                "Primary": "SE.SEC.CMPT.LO.ZS",
                "Forbidden": "enrollment — counts repeaters · spend — effort, "
                "not result · GDP — wealth, not schooling",
                "Threshold": "High ≥ 95% · Moderate ≥ 75%",  # tightened from 90
            },
        )
    )
    check(
        "ratified as a new version (never overwrites)",
        ratified.version == "v2",
        f"{ratified.version} · {ratified.remembered_on}",
    )

    v2_result = engine.handle(m.RunAnalysis(dataset_id="wdi", belief_id=""))
    v2_success = sum(1 for v in v2_result.verdicts if v.verdict == "Success")
    check(
        "tightened threshold moved verdicts on the same data",
        v2_success < v1_success,
        f"Success verdicts {v1_success} → {v2_success} (High ≥ 90 → 95)",
    )
    lines.append("")

    # ── 3 · Analysis ───────────────────────────────────────────────────────
    lines += ["## 3 · Analysis — verdicts · traps · receipt", ""]
    proof = json.loads((WAREHOUSE / "wdi" / "grounding_proof.json").read_text())

    lines.append(f"### wdi — {v1_result.belief_label.replace('Under: ', '')} (v1 run)")
    lines.append("")
    outside = sum(1 for v in v1_result.verdicts if v.outside)
    lines.append(
        f"- Verdicts: **{len(v1_result.verdicts)}** countries — "
        f"{len(v1_result.verdicts) - outside} evaluable, {outside} outside envelope"
    )
    lines.append(f"- {v1_result.thesis_note}")
    for t in v1_result.traps:
        lines.append(
            f"- Trap — **{t.entity}**: {t.decoy_name} {t.decoy_label} vs "
            f"{t.primary_name} {t.primary_label}; unguided read {t.unguided}, "
            f"belief says **{t.believed}**"
        )
    rc = v1_result.receipt
    lines.append(
        f"- Receipt: grounded **{rc.tokens} tok · {rc.series} series** vs "
        f"ungrounded **{rc.ungrounded_tokens} · {rc.ungrounded_series}**"
    )
    lines.append("")

    dry = proof["accuracy_vs_concept_truth_evaluable"]
    check(
        "disagreements match the BetaThon dry-run proof",
        v1_result.trap_count == dry["disagreements"],
        f"{v1_result.trap_count} vs proof {dry['disagreements']}",
    )
    check(
        "ungrounded receipt matches the dry-run proof",
        rc.ungrounded_tokens == proof["context_tokens_est"]["ungrounded_system_package"]
        and rc.ungrounded_series == proof["series_touches_total"]["ungrounded"],
        f"{rc.ungrounded_tokens} tok · {rc.ungrounded_series} series",
    )
    check(
        "grounded package within 5% of the dry-run 585",
        abs(rc.tokens - 585) <= 30,
        f"{rc.tokens} tok",
    )
    germany = next((t for t in v1_result.traps if t.entity == "Germany"), None)
    check(
        "the Germany enrollment-vs-completion trap is caught",
        germany is not None,
        germany and f"{germany.decoy_label} enrolled, {germany.primary_label} complete",
    )
    lines.append("")

    for ds_id in ("fiscal", "trade"):
        r = engine.handle(m.RunAnalysis(dataset_id=ds_id, belief_id=""))
        rc = r.receipt
        outside = sum(1 for v in r.verdicts if v.outside)
        lines += [
            f"### {ds_id} — {r.belief_label.replace('Under: ', '')}",
            "",
            f"- Verdicts: {len(r.verdicts)} entities — "
            f"{len(r.verdicts) - outside} evaluable, {outside} outside envelope",
            f"- {r.thesis_note}",
            f"- Receipt: grounded {rc.tokens} tok · {rc.series} series vs "
            f"ungrounded {rc.ungrounded_tokens} · {rc.ungrounded_series}",
            "",
        ]
        check(
            f"{ds_id}: grounding shrinks context and series",
            rc.tokens < rc.ungrounded_tokens and rc.series < rc.ungrounded_series,
        )

    # ── 4 · Live refresh (ingestion, network) ──────────────────────────────
    lines += ["## 4 · Live refresh — Eurostat", ""]
    if NETWORK:
        try:
            note = engine.handle(m.RefreshDataset(dataset_id="eurostat_edu_fin"))
            lines.append(f"> {note}")
            check("live Eurostat refresh + automatic belief re-run", bool(note))
        except Exception as e:
            lines.append(f"> refresh failed: {e}")
            check("live Eurostat refresh + automatic belief re-run", False, str(e))
    else:
        lines.append("> skipped (--no-network)")
    lines.append("")

    # ── 5 · Ledger ─────────────────────────────────────────────────────────
    lines += ["## 5 · Ledger — every run appended a row", ""]
    led = engine.handle(m.FetchLedger())
    lines.append("| Row | Tokens (with memory) | Tokens (without) |")
    lines.append("|-----|----------------------|------------------|")
    for i, p in enumerate(led.points):
        lines.append(f"| {p.episode} | {p.with_memory:,} | {p.without_memory:,} |")
    lines.append("")
    for t in led.tiles:
        lines.append(f"- **{t.value}** — {t.label}")
    lines.append("")
    expected_runs = 5 if NETWORK else 4  # cold seed + v1 + v2 + fiscal + trade (+ re-run)
    check(
        "ledger accumulated the session's runs",
        len(led.points) >= expected_runs,
        f"{len(led.points)} rows",
    )
    cold = led.points[0]
    warm = led.points[1]
    check(
        "the first-recall cliff is visible (ep1 cold → ep2 recalled)",
        warm.with_memory < cold.with_memory,
        f"{cold.with_memory:,} → {warm.with_memory:,}",
    )

    # ── 6 · Memory ─────────────────────────────────────────────────────────
    lines += ["", "## 6 · Memory — two histories, kept apart", ""]
    h = engine.handle(m.FetchBeliefHistory(belief_id="wdi"))
    lines.append(f"**{h.belief_name}** — {h.version_label}")
    lines.append("")
    for e in h.events:
        dot = "●" if e.kind == "belief" else "○"
        lines.append(f"- {dot} **{e.title}** {e.when} — {e.detail or e.note}")
    lines.append("")
    if h.compare_note:
        lines.append(f"> {h.compare_note}")
        lines.append("")
    belief_events = sum(1 for e in h.events if e.kind == "belief")
    data_events = sum(1 for e in h.events if e.kind == "data")
    check(
        "timeline separates belief changes from data runs",
        belief_events >= 2 and data_events >= 2,
        f"{belief_events} belief · {data_events} data events",
    )

    # ── 7 · Memory substrate — the EverOS storage root ────────────────────
    lines += ["", "## 7 · Memory substrate — remembered and recalled", ""]
    mem = concepts.memory()
    skill = (
        mem.root / "idatasight" / "wdi" / "agents" / USER / "skills"
        / "skill_secondary_completion"
    )
    refs = sorted(p.name for p in (skill / "references").glob("v*.json"))
    lines.append(
        f"Storage root (scratch): `{mem.root}` — pack plane holds {refs}, "
        f"episodes plane holds {len(mem.episodes(USER, 'wdi'))} booked runs."
    )
    lines.append("")
    check(
        "belief versions remembered append-only in the pack plane",
        refs == ["v1.json", "v2.json"],
        ", ".join(refs),
    )
    skill_md = (skill / "SKILL.md").read_text(encoding="utf-8") if (skill / "SKILL.md").exists() else ""
    check(
        "SKILL.md is the canon of the latest ratified declaration",
        "(v2)" in skill_md and "agent_skill" in skill_md,
    )
    recalled = mem.recall(USER, "wdi")
    check(
        "recall returns the remembered v2 with its parsed thresholds",
        recalled is not None
        and recalled["version"] == 2
        and recalled["thresholds"]["high"] == 95.0,
        recalled and f"v{recalled['version']} · high ≥ {recalled['thresholds']['high']:g}",
    )
    wdi_rows = [
        r["row"]
        for r in ledger_store.runs()
        if r["dataset"] == "wdi" and r["kind"] != "cold"
    ]
    booked = list(mem.episodes(USER, "wdi"))
    check(
        "every wdi run is booked as an episode in memory",
        booked == wdi_rows,
        f"episodes {booked} vs ledger rows {wdi_rows}",
    )

    # ── verdict ────────────────────────────────────────────────────────────
    lines += [
        "",
        "## Verdict",
        "",
        (
            "**ALL CHECKS PASSED** — ingestion, concept declaration, and "
            "analysis run on the real panels and reproduce the BetaThon "
            "dry-run proof."
            if not failures
            else f"**{len(failures)} CHECK(S) FAILED:** " + ", ".join(failures)
        ),
        "",
    ]

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nWrote {REPORT}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
