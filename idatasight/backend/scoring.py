"""Analysis — verdicts under a belief, traps caught, and the receipt.

Ported from BetaThon scripts/score_cases.py and scripts/proof_grounding.py.
Deterministic and offline: the grounded agent touches only the belief's
primary series; the ungrounded simulation blends whatever it finds, which is
exactly how the traps happen. Context-token estimates use the dry run's
construction, so the wdi receipt reproduces the proven 585-vs-1,399 numbers.
"""

from __future__ import annotations

import json

from ..models import AnalysisResult, Receipt, Trap, Verdict
from . import warehouse
from .warehouse import WAREHOUSE


def est_tokens(s: str) -> int:
    return max(1, len(s) // 4)


def grade(value: float | None, high: float, moderate: float, inverted: bool) -> str | None:
    if value is None:
        return None
    if inverted:  # lower is better (Gini)
        if value <= high:
            return "high"
        if value <= moderate:
            return "moderate"
        return "low"
    if value >= high:
        return "high"
    if value >= moderate:
        return "moderate"
    return "low"


def _fmt(value: float, unit: str) -> str:
    if unit.startswith("%"):
        return f"{value:.0f}%"
    if unit == "USD":
        return f"${value:,.0f}"
    return f"{value:,.1f}"


def _fmt_nd(value: float, unit: str, nd: int) -> str:
    if unit.startswith("%"):
        return f"{value:.{nd}f}%"
    if unit == "USD":
        return f"${value:,.{nd}f}"
    return f"{value:,.{max(nd, 1)}f}"


def _fmt_verdict(
    value: float, unit: str, high: float, moderate: float, inverted: bool
) -> str:
    """Format a verdict-bearing value so the display can never contradict
    the verdict: a reader must be able to recompute the grade from the number
    shown. Adds decimals only when rounding would cross a threshold
    (94.99 under High ≥ 95 renders as 94.99%, not 95%)."""
    fidelity = grade(value, high, moderate, inverted)
    start = 0 if unit.startswith("%") or unit == "USD" else 1
    for nd in range(start, 4):
        if grade(round(value, nd), high, moderate, inverted) == fidelity:
            return _fmt_nd(value, unit, nd)
    return _fmt_nd(value, unit, 4)


def _grounded_context(ds_id: str, belief: dict, cfg: dict) -> str:
    """The recalled pack — proof_grounding's grounded_context, with the
    ratified belief's statement and thresholds swapped in."""
    seed = _seed_record(ds_id, cfg)
    pkg = {
        "concept": belief["concept"],
        "genetic_identity": belief["statement"],
        "primary_series": cfg["primary"],
        "forbidden_proxies": sorted(cfg["forbidden"]),
        "excludes": (seed.get("boundaries") or {}).get("excludes", []),
        "rules": [r["statement"] for r in seed.get("rules", [])]
        or [
            "Using a forbidden proxy series for success leaves this concept.",
            "A missing primary observation is outside the envelope, never failure.",
        ],
        "thresholds": belief.get("thresholds", cfg["thresholds"]),
        "envelope": seed.get("fidelity_envelope", {}),
    }
    return "GROUNDED_CONTEXT\n" + json.dumps(pkg, indent=2)


def _seed_record(ds_id: str, cfg: dict) -> dict:
    from .concepts import CONCEPT_SEEDS  # no cycle: concepts doesn't import scoring

    for p in (
        CONCEPT_SEEDS / f"{cfg['name']}.json",
        CONCEPT_SEEDS / "by_dataset" / f"{ds_id}__{cfg['name']}.json",
    ):
        if p.exists():
            return json.loads(p.read_text())
    return {}


def _ungrounded_context(ds_id: str) -> str:
    """Full-catalog dump — proof_grounding's ungrounded_context: the whole
    indicators file plus every code, dragged into the prompt."""
    ind_path = WAREHOUSE / ds_id / "indicators.csv"
    catalog = ind_path.read_text(encoding="utf-8") if ind_path.exists() else ""
    codes = sorted({m.get("code", "") for m in warehouse.load_indicators(ds_id)})
    return (
        "You are a data agent. Full indicator catalog follows. "
        "Rank countries by education quality using any series you like.\n"
        + catalog
        + "\nCODES="
        + ",".join(codes)
    )


def _ungrounded_answer(ds_id: str, vals: dict, cfg: dict) -> tuple[bool | None, int]:
    """(success claim, series touched) for the unguided blend —
    proof_grounding's education blend for wdi, run_five's avg blend else."""
    if ds_id == "wdi":
        enrr = vals.get("SE.SEC.ENRR")
        spend = vals.get("SE.XPD.TOTL.GD.ZS")
        gdp = vals.get("NY.GDP.PCAP.CD")
        parts = []
        touched = 0
        if enrr is not None:
            parts.append(min(enrr, 120) / 120 * 40)
            touched += 1
        if spend is not None:
            parts.append(min(spend, 8) / 8 * 30)
            touched += 1
        if gdp is not None:
            parts.append(min(gdp, 80000) / 80000 * 30)
            touched += 1
        return (sum(parts) >= 55 if parts else None), touched
    if not vals:
        return None, 0
    avg = sum(vals.values()) / len(vals)
    if cfg["inverted"]:
        return avg < cfg["thresholds"]["moderate"], len(vals)
    return avg > cfg["thresholds"]["moderate"], len(vals)


def analyze(ds_id: str, belief: dict) -> AnalysisResult:
    cfg = warehouse.concept_cfg(ds_id)
    thresholds = belief.get("thresholds") or cfg["thresholds"]
    high, moderate = thresholds["high"], thresholds["moderate"]
    inverted = cfg["inverted"]
    unit = cfg["unit"]
    primary = cfg["primary"]
    decoy = cfg.get("decoy") or ""

    best, names = warehouse.panel_best(ds_id)

    verdicts: list[Verdict] = []
    trap_candidates: list[tuple[int, Trap]] = []
    disagreements = 0
    evaluable = 0
    ug_match = 0
    ug_series = 0
    g_series = 0

    for key in sorted(best, key=lambda k: names.get(k, k)):
        vals = best[key]
        entity = names.get(key, key)
        pv = vals.get(primary)
        g_series += 1  # the grounded agent asks for the primary, always
        ug_success, touched = _ungrounded_answer(ds_id, vals, cfg)
        ug_series += touched

        if pv is None:
            verdicts.append(Verdict(entity, "—", "outside envelope", outside=True))
            continue

        evaluable += 1
        fidelity = grade(pv, high, moderate, inverted)
        success = fidelity == "high"
        # Three bands, per wireframe 1f — a moderate-threshold edit must be
        # visible in the verdicts, not collapsed into "Not yet".
        label = {"high": "Success", "moderate": "Moderate", "low": "Not yet"}[fidelity]
        verdicts.append(
            Verdict(
                entity,
                _fmt_verdict(pv, unit, high, moderate, inverted),
                label,
            )
        )

        if ug_success is None:
            continue
        if bool(ug_success) == bool(success):
            ug_match += 1
            continue
        disagreements += 1
        dv = vals.get(decoy)
        if dv is None:
            continue
        scale = max(dv, pv, 100.0 if unit.startswith("%") else 0.0)
        trap = Trap(
            entity=entity,
            decoy_name=_decoy_label(decoy),
            decoy_label=_fmt(dv, unit if unit.startswith("%") else ""),
            decoy_width=f"{min(100, dv / scale * 100):.0f}%",
            primary_name=_primary_label(ds_id),
            primary_label=_fmt_verdict(pv, unit, high, moderate, inverted),
            primary_width=f"{min(100, pv / scale * 100):.0f}%",
            unguided="“success”" if ug_success else "“not yet”",
            believed="not yet" if ug_success else "success",
        )
        # the dangerous direction first: unguided flattery, belief says no
        rank = 0 if (ug_success and not success) else 1
        trap_candidates.append((rank, trap))

    trap_candidates.sort(key=lambda rt: rt[0])
    traps = [t for _, t in trap_candidates[:2]]

    g_ctx = _grounded_context(ds_id, belief, cfg)
    ug_ctx = _ungrounded_context(ds_id)
    match_pct = round(100 * ug_match / evaluable, 1) if evaluable else 0.0

    receipt = Receipt(
        tokens=est_tokens(g_ctx),
        series=g_series,
        ungrounded_tokens=est_tokens(ug_ctx),
        ungrounded_series=ug_series,
        ledger_row=0,  # engine fills after appending
    )

    version = belief.get("version", 1)
    display = belief.get("display_name", cfg["display_name"])
    return AnalysisResult(
        belief_label=f"Under: {display} · v{version}",
        verdicts=verdicts,
        traps=traps,
        trap_count=disagreements,
        thesis_note=(
            f"{disagreements} of {evaluable} verdicts differ from the "
            f"unguided blend ({match_pct:g}% match) — your belief changed the answer"
        ),
        receipt=receipt,
    )


def _decoy_label(decoy: str) -> str:
    labels = {
        "SE.SEC.ENRR": "enrollment",
        "NY.GDP.PCAP.CD": "GDP/capita",
        "NE.IMP.GNFS.ZS": "imports",
        "SL.UEM.TOTL.ZS": "unemployment",
        "NY.GNP.PCAP.CD": "GNI/capita",
    }
    return labels.get(decoy, decoy.lower())


def _primary_label(ds_id: str) -> str:
    labels = {
        "wdi": "completion",
        "fiscal": "gov. expense",
        "trade": "exports",
        "labor_hc": "participation",
        "inequality": "Gini",
        "eurostat_edu_fin": "edu spend",
    }
    return labels.get(ds_id, "primary")
