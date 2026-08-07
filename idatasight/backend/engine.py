"""Engine — the actor bodies behind dispatch(), pending TAOpy.

Each handler below is the functionality one TAOpy actor will own in phase 2
(the message → actor map lives in hooks.py). The logic is ported from the
BetaThon dry runs and works on the real panels in data/warehouse/.
"""

from __future__ import annotations

from typing import Any

from ..config import USER
from ..models import ColumnInfo, Dataset
from . import concepts, ingest, ledger_store, scoring, warehouse
from . import messages as m


def _list_datasets() -> list[Dataset]:
    out = []
    for ds_id, entry in warehouse.REGISTRY.items():
        stats = warehouse.dataset_stats(ds_id)
        out.append(
            Dataset(
                id=ds_id,
                name=entry["name"],
                source=entry["source"],
                summary=stats["summary"],
                refreshed=stats["refreshed"],
                beliefs_attached=concepts.count_watching(ds_id),
            )
        )
    return out


def _fetch_columns(ds_id: str) -> list[ColumnInfo]:
    return [
        ColumnInfo(indicator=code, unit=unit, meaning=meaning)
        for code, unit, meaning in warehouse.column_infos(ds_id)
    ]


def _run_analysis(ds_id: str, kind: str = "run") -> Any:
    belief = concepts.current(ds_id)  # recalled from memory, not re-declared
    result = scoring.analyze(ds_id, belief)
    row = ledger_store.append(
        {
            "kind": kind,
            "dataset": ds_id,
            "concept": belief["concept"],
            "version": belief["version"],
            "grounded_tokens": result.receipt.tokens,
            "ungrounded_tokens": result.receipt.ungrounded_tokens,
            "grounded_series": result.receipt.series,
            "ungrounded_series": result.receipt.ungrounded_series,
            "match_pct": 100.0,  # grounded is definitionally true to the belief
            "verdicts": sum(1 for v in result.verdicts if not v.outside),
        }
    )
    result.receipt.ledger_row = row
    # Ledger rows stay in the application; the run itself is booked to memory.
    concepts.memory().remember_episode(
        USER,
        ds_id,
        row,
        note=(
            f"{kind} under {belief['concept']} v{belief['version']} · "
            f"{result.receipt.tokens} tokens · ledger row #{row}"
        ),
    )
    return result


def _refresh_dataset(ds_id: str) -> str:
    """Re-ingest, then re-run the remembered belief — the compounding moment."""
    counts = ingest.refresh(ds_id)
    result = _run_analysis(ds_id, kind="re-run")
    changed = sum(1 for v in result.verdicts if not v.outside)
    return (
        f"refreshed — {counts['rows']:,} rows ({counts['delta']:+,} vs before) · "
        f"belief re-ran automatically · {changed} verdicts, "
        f"logged → ledger row #{result.receipt.ledger_row}"
    )


def handle(msg: Any) -> Any:
    match msg:
        case m.ListDatasets():
            return _list_datasets()
        case m.FetchColumns(dataset_id=ds_id):
            return _fetch_columns(ds_id or "wdi")
        case m.RefreshDataset(dataset_id=ds_id):
            return _refresh_dataset(ds_id or "wdi")
        case m.DraftGrounding(hypothesis=h, dataset_id=ds_id):
            return concepts.draft_grounding(h, ds_id or "wdi")
        case m.RatifyBelief(dataset_id=ds_id, statement=s, fields=f):
            return concepts.ratify(ds_id or "wdi", s, f)
        case m.ListBeliefs(dataset_id=ds_id):
            return concepts.list_beliefs(ds_id)
        case m.FetchBeliefHistory(belief_id=belief_id):
            ds_id = belief_id if belief_id in warehouse.REGISTRY else "wdi"
            return concepts.history(ds_id, ledger_store.runs())
        case m.RunAnalysis(dataset_id=ds_id):
            return _run_analysis(ds_id or "wdi")
        case m.FetchLedger():
            return ledger_store.fetch()
    return None
