"""Application state — every backend touch goes through call().

call() sends the typed message through hooks.dispatch (the TAOpy seam) and,
while the actors don't exist yet, falls back to the demo stand-in when
config.DEMO_MODE is on.
"""

from typing import Any

import reflex as rx

from .backend import demo
from .backend import messages as m
from .backend.hooks import dispatch
from .config import DEMO_MODE
from .models import (
    Analyst,
    ColumnInfo,
    Dataset,
    GroundingField,
    LedgerPoint,
    MemoryItem,
    Receipt,
    Tile,
    TimelineEvent,
    Trap,
    Verdict,
)


async def call(msg: Any) -> Any:
    """Dispatch a message; fall back to demo content until phase 2."""
    result = await dispatch(msg)
    if result is None and DEMO_MODE:
        result = demo.reply(msg)
    return result


class AppState(rx.State):
    """One state tree for the five-page loop."""

    # --- Datasets ----------------------------------------------------------
    datasets: list[Dataset] = []
    columns: list[ColumnInfo] = []
    selected_dataset_id: str = ""
    refresh_note: str = ""

    # --- Beliefs -----------------------------------------------------------
    hypothesis: str = ""
    draft_fields: list[GroundingField] = []
    drafted: bool = False
    ratified_version: str = ""
    remembered_on: str = ""
    ratify_error: str = ""

    # --- Analysis ----------------------------------------------------------
    belief_label: str = ""
    verdicts: list[Verdict] = []
    traps: list[Trap] = []
    trap_count: int = 0
    thesis_note: str = ""
    receipt: Receipt = Receipt()
    has_run: bool = False

    # --- Ledger ------------------------------------------------------------
    ledger_points: list[dict] = []
    ledger_tiles: list[Tile] = []
    ledger_rows: list[MemoryItem] = []

    # --- Memory ------------------------------------------------------------
    belief_name: str = ""
    version_label: str = ""
    analysts: list[Analyst] = []
    timeline: list[TimelineEvent] = []
    compare_note: str = ""

    # --- Rail --------------------------------------------------------------
    beliefs: list[MemoryItem] = []

    # === computed ==========================================================

    @rx.var
    def selected_dataset(self) -> Dataset:
        for d in self.datasets:
            if d.id == self.selected_dataset_id:
                return d
        return Dataset()

    @rx.var
    def all_ratified(self) -> bool:
        return bool(self.draft_fields) and all(
            f.ratified for f in self.draft_fields
        )

    # === event handlers ====================================================

    # --- Datasets ----------------------------------------------------------

    @rx.event
    async def load_datasets(self):
        self.beliefs = await call(m.ListBeliefs()) or []
        self.datasets = await call(m.ListDatasets()) or []
        if self.datasets and not self.selected_dataset_id:
            self.selected_dataset_id = self.datasets[0].id
        await self._load_columns()

    async def _load_columns(self):
        self.columns = (
            await call(m.FetchColumns(dataset_id=self.selected_dataset_id))
            or []
        )

    @rx.event
    async def select_dataset(self, dataset_id: str):
        self.selected_dataset_id = dataset_id
        self.has_run = False  # next analysis judges the newly chosen dataset
        self.beliefs = await call(m.ListBeliefs(dataset_id=dataset_id)) or []
        await self._load_columns()

    @rx.event
    async def refresh_dataset(self):
        self.refresh_note = "refreshing from source — beliefs will re-run…"
        yield
        result = await call(m.RefreshDataset(dataset_id=self.selected_dataset_id))
        self.refresh_note = (
            result
            if isinstance(result, str)
            else "refresh failed — check the connection and try again"
        )
        self.has_run = False
        self.datasets = await call(m.ListDatasets()) or self.datasets

    # --- Beliefs -----------------------------------------------------------

    @rx.event
    async def load_beliefs_page(self):
        self.beliefs = await call(m.ListBeliefs()) or []
        if not self.hypothesis:
            remembered = await call(
                m.RecallBelief(dataset_id=self.selected_dataset_id or "wdi")
            )
            if remembered:
                self.hypothesis = remembered.get("statement", "")
            elif DEMO_MODE:
                self.hypothesis = demo.HYPOTHESIS

    @rx.event
    def set_hypothesis(self, value: str):
        self.hypothesis = value

    @rx.event
    async def draft_grounding(self):
        draft = await call(
            m.DraftGrounding(
                hypothesis=self.hypothesis,
                dataset_id=self.selected_dataset_id,
            )
        )
        self.draft_fields = draft.fields if draft else []
        self.drafted = bool(self.draft_fields)
        self.ratified_version = ""

    @rx.event
    def ratify_field(self, key: str):
        for f in self.draft_fields:
            if f.key == key:
                f.ratified = True
                f.editing = False

    @rx.event
    def edit_field(self, key: str):
        for f in self.draft_fields:
            if f.key == key:
                f.editing = not f.editing
                f.ratified = False

    @rx.event
    def set_field_value(self, key: str, value: str):
        for f in self.draft_fields:
            if f.key == key:
                f.value = value

    @rx.event
    async def ratify_belief(self):
        result = await call(
            m.RatifyBelief(
                dataset_id=self.selected_dataset_id,
                statement=self.hypothesis,
                fields={f.key: f.value for f in self.draft_fields},
            )
        )
        if result:
            self.ratified_version = result.version
            self.remembered_on = result.remembered_on
            self.ratify_error = ""
            self.beliefs = await call(m.ListBeliefs()) or []
            self.has_run = False  # next run recalls the new version
        else:
            self.ratified_version = ""
            self.ratify_error = (
                "not remembered — the commit to memory failed; "
                "nothing was written. Check the app log and ratify again."
            )

    # --- Analysis ----------------------------------------------------------

    @rx.event
    async def run_analysis(self):
        result = await call(
            m.RunAnalysis(
                dataset_id=self.selected_dataset_id,
                belief_id=self.belief_label,
            )
        )
        if result:
            self.belief_label = result.belief_label
            self.verdicts = result.verdicts
            self.traps = result.traps
            self.trap_count = result.trap_count
            self.thesis_note = result.thesis_note
            self.receipt = result.receipt
            self.has_run = True

    @rx.event
    async def load_analysis(self):
        self.beliefs = await call(m.ListBeliefs()) or []
        if not self.has_run:
            await self.run_analysis()

    # --- Ledger ------------------------------------------------------------

    @rx.event
    async def load_ledger(self):
        data = await call(m.FetchLedger())
        if data:
            self.ledger_points = [
                {
                    "episode": p.episode,
                    "with memory": p.with_memory,
                    "without memory": p.without_memory,
                }
                for p in data.points
            ]
            self.ledger_tiles = data.tiles
            self.ledger_rows = data.rows

    # --- Memory ------------------------------------------------------------

    @rx.event
    async def load_memory(self):
        self.beliefs = await call(m.ListBeliefs()) or []
        history = await call(
            m.FetchBeliefHistory(belief_id=self.selected_dataset_id or "wdi")
        )
        if history:
            self.belief_name = history.belief_name
            self.version_label = history.version_label
            self.analysts = history.analysts
            self.timeline = history.events
            self.compare_note = history.compare_note

    @rx.event
    def select_analyst(self, name: str):
        self.analysts = [
            Analyst(
                name=a.name,
                belief_label=a.belief_label,
                selected=a.name == name,
            )
            for a in self.analysts
        ]
