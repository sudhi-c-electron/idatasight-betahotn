"""Concept declarations — draft, ratify, versioned memory.

Seeds come from the BetaThon formal Concept records (data/concepts/*.json).
Ratified versions live in EverOS memory (backend/everos.py — the storage-root
pack plane, per-analyst, append-only): a version is never overwritten;
reopening a belief drafts the next one. The UI vocabulary stays belief /
remembered / recalled — the substrate's name never appears on screen.
"""

from __future__ import annotations

import json
import re
from datetime import datetime

from ..config import USER
from ..models import (
    Analyst,
    BeliefHistory,
    GroundingDraft,
    GroundingField,
    MemoryItem,
    RatifyResult,
    TimelineEvent,
)
from . import warehouse
from .everos import EverOSMemory
from .warehouse import APP_ROOT, REGISTRY

CONCEPT_SEEDS = APP_ROOT / "data" / "concepts"

_memory: EverOSMemory | None = None


def memory() -> EverOSMemory:
    """The EverOS memory, bound on first use (honors EVEROS_ROOT)."""
    global _memory
    if _memory is None:
        _memory = EverOSMemory()
    return _memory


def _versions(ds_id: str) -> list[dict]:
    """All remembered versions of this dataset's belief, oldest first."""
    return memory().history(USER, ds_id)


def _seed_statement(ds_id: str) -> str:
    """The formal Concept's genetic identity, from the BetaThon record."""
    cfg = REGISTRY[ds_id]["concept"]
    candidates = [
        CONCEPT_SEEDS / f"{cfg['name']}.json",
        CONCEPT_SEEDS / "by_dataset" / f"{ds_id}__{cfg['name']}.json",
    ]
    for p in candidates:
        if p.exists():
            return json.loads(p.read_text()).get("genetic_identity", "")
    return cfg["definition"]


def _threshold_text(cfg: dict, thresholds: dict | None = None) -> str:
    th = thresholds or cfg["thresholds"]
    unit = cfg.get("unit", "")
    suffix = "%" if unit.startswith("%") else ""
    if cfg.get("inverted"):
        return f"High ≤ {th['high']:g}{suffix} · Moderate ≤ {th['moderate']:g}{suffix}"
    return f"High ≥ {th['high']:g}{suffix} · Moderate ≥ {th['moderate']:g}{suffix}"


def _forbidden_text(cfg: dict) -> str:
    if not cfg["forbidden"]:
        return "—"
    return " · ".join(dict.fromkeys(cfg["forbidden"].values()))


def ensure_seed(ds_id: str) -> None:
    """Remember v1 from the formal BetaThon Concept on first touch."""
    if _versions(ds_id):
        return
    cfg = warehouse.concept_cfg(ds_id)
    v1 = {
        "version": 1,
        "concept": cfg["name"],
        "display_name": cfg["display_name"],
        "statement": _seed_statement(ds_id),
        "fields": {
            "Definition": cfg["definition"],
            "Primary": cfg["primary"],
            "Forbidden": _forbidden_text(cfg),
            "Threshold": _threshold_text(cfg),
        },
        "thresholds": cfg["thresholds"],
        "ratified_on": "2026-08-07",
        "origin": "seed — BetaThon dry run",
    }
    memory().remember_pack(USER, ds_id, v1)


def draft_grounding(hypothesis: str, ds_id: str) -> GroundingDraft:
    """Distill plain words into a proposed grounding pack.

    Deterministic distillation (BetaThon style, no LLM): the dataset's bound
    formal Concept supplies the anatomy; the hypothesis stays the statement.
    """
    cfg = warehouse.concept_cfg(ds_id)
    return GroundingDraft(
        fields=[
            GroundingField(key="Definition", value=cfg["definition"]),
            GroundingField(key="Primary", value=cfg["primary"], mono=True),
            GroundingField(key="Forbidden", value=_forbidden_text(cfg)),
            GroundingField(key="Threshold", value=_threshold_text(cfg)),
        ]
    )


def _parse_thresholds(text: str, cfg: dict) -> dict:
    """Pull the two numbers out of an edited Threshold field; keep defaults
    when the edit isn't parseable."""
    nums = re.findall(r"(\d+(?:\.\d+)?)", text or "")
    if len(nums) >= 2:
        return {"high": float(nums[0]), "moderate": float(nums[1])}
    return dict(cfg["thresholds"])


def ratify(ds_id: str, statement: str, fields: dict) -> RatifyResult:
    """Commit a human-confirmed pack as the next remembered version.

    The declaration is preserved as declared — a canon write to the pack
    plane; a version, once remembered, is never overwritten.
    """
    ensure_seed(ds_id)
    cfg = warehouse.concept_cfg(ds_id)
    versions = _versions(ds_id)
    n = versions[-1]["version"] + 1 if versions else 1
    today = datetime.now().strftime("%Y-%m-%d")
    record = {
        "version": n,
        "concept": cfg["name"],
        "display_name": cfg["display_name"],
        "statement": statement,
        "fields": fields,
        "thresholds": _parse_thresholds(fields.get("Threshold", ""), cfg),
        "ratified_on": today,
        "origin": "ratified in iDataSight",
    }
    memory().remember_pack(USER, ds_id, record)
    return RatifyResult(
        version=f"v{n}", remembered_on=datetime.now().strftime("%b %-d, %Y")
    )


def current(ds_id: str) -> dict:
    """Latest ratified version (seeding v1 if the store is empty)."""
    ensure_seed(ds_id)
    return _versions(ds_id)[-1]


def list_beliefs(ds_id: str = "") -> list[MemoryItem]:
    """Rail content. One entry per dataset belief; latest version noted."""
    ids = [ds_id] if ds_id else list(REGISTRY)
    items = []
    for i in ids:
        ensure_seed(i)
        versions = _versions(i)
        latest = versions[-1]
        note = f"v{latest['version']}"
        note += " · remembered" if len(versions) == 1 else f" · {len(versions)} versions"
        items.append(
            MemoryItem(
                name=latest.get("display_name", latest["concept"]),
                note=note,
                highlight=latest.get("origin", "").startswith("ratified"),
            )
        )
    if not any(m.highlight for m in items) and items:
        items[0].highlight = True
    return items


def count_watching(ds_id: str) -> int:
    """How many formal Concepts bind into this dataset's columns — a seed
    concept watches a dataset when its primary series is one of its columns."""
    inds = set(REGISTRY[ds_id]["indicators"])
    seen: set[str] = set()
    seeds = list(CONCEPT_SEEDS.glob("*.json")) + list(
        (CONCEPT_SEEDS / "by_dataset").glob("*.json")
    )
    for p in seeds:
        c = json.loads(p.read_text())
        name = c.get("name", p.stem)
        if name in seen:
            continue
        primary = (c.get("series_bindings") or {}).get("primary") or ""
        primaries = primary if isinstance(primary, list) else [primary]
        if (inds and any(p in inds for p in primaries)) or c.get("dataset") == ds_id:
            seen.add(name)
    return max(len(seen), 1)


def _field_diff(prev: dict, cur: dict) -> str:
    parts = []
    for key in ("Definition", "Primary", "Forbidden", "Threshold"):
        a = (prev.get("fields") or {}).get(key, "")
        b = (cur.get("fields") or {}).get(key, "")
        if a != b:
            parts.append(f"{key}: {a or '—'} → {b or '—'}")
    return " · ".join(parts) if parts else "re-ratified without field changes"


def history(ds_id: str, ledger_runs: list[dict]) -> BeliefHistory:
    """Both histories, kept apart: belief versions (meaning moved) and
    runs/refreshes from the ledger (verdicts moved)."""
    ensure_seed(ds_id)
    versions = _versions(ds_id)
    cfg = warehouse.concept_cfg(ds_id)

    dated: list[tuple[str, TimelineEvent]] = []
    for i, v in enumerate(versions):
        when = datetime.strptime(v["ratified_on"], "%Y-%m-%d").strftime("%b %Y")
        if i == 0:
            detail = f"“{v['statement'][:110]}”"
            title = "v1 — declared"
        else:
            detail = _field_diff(versions[i - 1], v)
            title = f"v{v['version']} — revised"
        dated.append(
            (
                v["ratified_on"],
                TimelineEvent(kind="belief", title=title, when=when, detail=detail),
            )
        )
    for run in ledger_runs:
        if run.get("dataset") != ds_id:
            continue
        kind_label = {
            "cold": "cold run", "run": "run", "re-run": "auto re-run"
        }.get(run.get("kind", "run"), "run")
        recalled = (
            f"recalled v{run.get('version')} · " if run.get("version") else ""
        )
        dated.append(
            (
                run.get("at", ""),
                TimelineEvent(
                    kind="data",
                    title=f"Row #{run['row']} — {kind_label} · {run.get('verdicts', 0)} verdicts",
                    note=(
                        f"{recalled}{run.get('grounded_tokens', 0):,} tokens · "
                        f"{run.get('match_pct', 0):g}% vs declared truth"
                    ),
                ),
            )
        )
    # ISO date/timestamp strings sort chronologically; newest first on screen.
    dated.sort(key=lambda de: de[0])
    events = [e for _, e in reversed(dated)]

    analysts = [Analyst(name="You", selected=True)]
    compare = ""
    if ds_id == "wdi":
        analysts.append(Analyst(name="Maya", belief_label="effort belief"))
        compare = _completion_vs_effort_note()

    latest = versions[-1]
    return BeliefHistory(
        belief_name=latest.get("display_name", cfg["display_name"]),
        version_label=f"Edit → v{latest['version'] + 1}",
        analysts=analysts,
        events=events,
        compare_note=compare,
    )


def _completion_vs_effort_note() -> str:
    """Real divergence between the completion and effort beliefs on the same
    panel (BetaThon score_cases divergence logic, latest non-null values)."""
    best, names = warehouse.panel_best("wdi")
    completion_cfg = REGISTRY["wdi"]["concept"]
    diverged = []
    for key, vals in best.items():
        c = vals.get(completion_cfg["primary"])
        spend = vals.get("SE.XPD.TOTL.GD.ZS")
        if c is None or spend is None:
            continue
        effort_success = spend >= 5.0  # public_education_effort high threshold
        completion_success = c >= completion_cfg["thresholds"]["high"]
        if effort_success and not completion_success:
            diverged.append(names.get(key, key))
    if not diverged:
        return ""
    n = len(diverged)
    sample = ", ".join(sorted(diverged)[:3])
    noun = "country" if n == 1 else "countries"
    return (
        f"Same data, two beliefs — the “effort” belief calls {n} {noun} "
        f"a success that “completion” does not ({sample}). "
        "Both provably right, each under its own belief."
    )
