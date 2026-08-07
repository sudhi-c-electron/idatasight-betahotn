"""Ledger — every run appends a row; the chart is a live query, not a slide.

The store is data/store/ledger.json. Row #1 is seeded from the BetaThon dry
run's cold (ungrounded) episode — grounding_proof.json, copied with the data —
so the "first recall" cliff in the chart is the real historical one.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..models import LedgerData, LedgerPoint, MemoryItem, Tile
from .warehouse import APP_ROOT, WAREHOUSE

LEDGER = APP_ROOT / "data" / "store" / "ledger.json"


def _load() -> list[dict]:
    if LEDGER.exists():
        return json.loads(LEDGER.read_text()).get("runs", [])
    return []


def _save(runs: list[dict]) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps({"runs": runs}, indent=2))


def ensure_seed() -> None:
    """Row #1: the BetaThon dry run's cold episode (real numbers)."""
    if _load():
        return
    proof = WAREHOUSE / "wdi" / "grounding_proof.json"
    if not proof.exists():
        return
    p = json.loads(proof.read_text())
    ct = p["context_tokens_est"]
    acc = p["accuracy_vs_concept_truth_evaluable"]
    _save(
        [
            {
                "row": 1,
                "kind": "cold",
                "dataset": "wdi",
                "concept": "secondary_completion",
                "version": 0,
                "grounded_tokens": ct["ungrounded_system_package"],
                "ungrounded_tokens": ct["ungrounded_system_package"],
                "grounded_series": p["series_touches_total"]["ungrounded"],
                "ungrounded_series": p["series_touches_total"]["ungrounded"],
                "match_pct": acc["ungrounded_match_pct"],
                "verdicts": p["evaluable_under_completion_concept"],
                "at": "2026-08-07T00:00:00",
                "note": "BetaThon dry run — no pack recalled",
            }
        ]
    )


def append(run: dict) -> int:
    """Append a run row; returns its row number."""
    ensure_seed()
    runs = _load()
    run["row"] = runs[-1]["row"] + 1 if runs else 1
    run.setdefault("at", datetime.now().isoformat(timespec="seconds"))
    runs.append(run)
    _save(runs)
    return run["row"]


def runs() -> list[dict]:
    ensure_seed()
    return _load()


def fetch() -> LedgerData:
    rows = runs()
    if not rows:
        return LedgerData()

    points = [
        LedgerPoint(
            episode=f"ep {i + 1}",
            with_memory=r["grounded_tokens"],
            without_memory=r["ungrounded_tokens"],
        )
        for i, r in enumerate(rows)
    ]

    tiles: list[Tile] = []
    warm = [r for r in rows if r["kind"] != "cold"]
    first_warm = next((i + 1 for i, r in enumerate(rows) if r["kind"] != "cold"), None)
    if first_warm:
        tiles.append(Tile(f"run {first_warm}", "pack pays for itself", accent=True))
    if warm:
        red = sum(
            1 - r["grounded_tokens"] / r["ungrounded_tokens"]
            for r in warm
            if r["ungrounded_tokens"]
        ) / len(warm)
        tiles.append(Tile(f"−{red * 100:.0f}%", "every run after"))
    cum_g = sum(r["grounded_tokens"] for r in rows)
    cum_u = sum(r["ungrounded_tokens"] for r in rows)
    tiles.append(Tile(f"{cum_g:,}", f"cumulative vs {cum_u:,}"))

    rail = [
        MemoryItem(
            name=f"row #{r['row']} · {r['kind']}",
            note=f"{r['grounded_tokens']:,} tok · "
            + ("auto" if r["kind"] == "re-run" else f"{r['match_pct']:g}%"),
        )
        for r in reversed(rows[-6:])
    ]
    return LedgerData(points=points, tiles=tiles, rows=rail)
