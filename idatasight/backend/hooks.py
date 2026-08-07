"""The backend seam — one dispatch.

Today dispatch routes every message to engine.py, which carries the real
ingestion / concept-declaration / analysis / ledger logic ported from the
BetaThon dry runs (local CSV panels by default, Snowflake BETATHON via
IDATASIGHT_SOURCE=snowflake).

Phase 2 (TAOpy): this module composes the ActorSystem and the engine handlers
become the actor bodies, roughly:

    system = ActorSystem(sinks=[...])
    system.tao_spawn("dataset-actor",  DatasetActor(tracer=system.tao_hub))
    system.tao_spawn("belief-actor",   BeliefActor(tracer=system.tao_hub))
    system.tao_spawn("analysis-actor", AnalysisActor(tracer=system.tao_hub))
    system.tao_spawn("ledger-actor",   LedgerActor(tracer=system.tao_hub))

    ACTOR_FOR = {
        ListDatasets: "dataset-actor", FetchColumns: "dataset-actor",
        RefreshDataset: "dataset-actor",
        DraftGrounding: "belief-actor", RatifyBelief: "belief-actor",
        ListBeliefs: "belief-actor", FetchBeliefHistory: "belief-actor",
        RunAnalysis: "analysis-actor", FetchLedger: "ledger-actor",
    }

    async def dispatch(msg):
        return await system.tao_ask(ACTOR_FOR[type(msg)], msg)

The messages in messages.py become tao.Event value objects; nothing in the UI
changes.
"""

import asyncio
import traceback
from typing import Any

from . import engine


async def dispatch(msg: Any) -> Any:
    """Route a message from messages.py to its handler.

    Engine work is file/CPU/network-bound — run it off the event loop. On any
    failure return None so the UI can fall back (demo content in DEMO_MODE).
    """
    try:
        return await asyncio.to_thread(engine.handle, msg)
    except Exception:
        print(f"[hooks] dispatch failed for {type(msg).__name__}:")
        traceback.print_exc()
        return None
