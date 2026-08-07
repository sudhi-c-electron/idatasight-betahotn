"""Demo content — the wireframe's education example, verbatim where possible.

reply(msg) mirrors hooks.dispatch(msg): given a message from messages.py it
returns the same shape the TAOpy actors will return in phase 2. State calls it
only when dispatch() came back empty and config.DEMO_MODE is on.
"""

from typing import Any

from ..models import (
    AnalysisResult,
    Analyst,
    BeliefHistory,
    ColumnInfo,
    Dataset,
    GroundingDraft,
    GroundingField,
    LedgerData,
    LedgerPoint,
    MemoryItem,
    Receipt,
    Tile,
    TimelineEvent,
    Trap,
    Verdict,
)
from . import messages as m

DATASETS = [
    Dataset(
        id="edu-panel",
        name="Education panel",
        source="World Bank WDI",
        summary="29 countries · 2010–2023 · 4,872 rows",
        refreshed="refreshed Aug 2026",
        beliefs_attached=2,
    ),
    Dataset(
        id="fiscal",
        name="Fiscal",
        source="World Bank",
        summary="41 countries · 2000–2024 · 6,110 rows",
        refreshed="refreshed Jul 2026",
    ),
    Dataset(
        id="trade",
        name="Trade",
        source="World Bank",
        summary="63 countries · 1995–2024 · 9,480 rows",
        refreshed="refreshed Jul 2026",
    ),
    Dataset(
        id="labor",
        name="Labor",
        source="World Bank",
        summary="48 countries · 2005–2024 · 5,232 rows",
        refreshed="refreshed Jun 2026",
    ),
    Dataset(
        id="inequality",
        name="Inequality",
        source="World Bank",
        summary="37 countries · 2000–2023 · 3,914 rows",
        refreshed="refreshed May 2026",
    ),
    Dataset(
        id="eu-edu-finance",
        name="EU edu finance",
        source="Eurostat",
        summary="27 countries · 2012–2024 · 3,205 rows",
        refreshed="refreshed Aug 2026",
    ),
]

COLUMNS = [
    ColumnInfo("SE.SEC.CMPT.LO.ZS", "%", "who finishes lower-secondary school"),
    ColumnInfo("SE.SEC.ENRR", "%", "who is enrolled — incl. repeaters, can top 100"),
    ColumnInfo("SE.XPD.TOTL.GD.ZS", "% GDP", "what government spends on education"),
    ColumnInfo("SE.TER.ENRR", "%", "who is enrolled in tertiary education"),
    ColumnInfo("NY.GDP.PCAP.CD", "USD", "output per person — wealth, not schooling"),
]

HYPOTHESIS = (
    "Government spending does not equal secondary completion. "
    "Effort is not outcome."
)

GROUNDING_DRAFT = GroundingDraft(
    fields=[
        GroundingField(
            key="Definition",
            value="success = completing secondary school, not being in it",
        ),
        GroundingField(key="Primary", value="SE.SEC.CMPT.LO.ZS", mono=True),
        GroundingField(
            key="Forbidden",
            value=(
                "enrollment — counts repeaters · spend — effort, not result · "
                "GDP — wealth, not schooling"
            ),
        ),
        GroundingField(key="Threshold", value="High ≥ 90% · Moderate ≥ 75%"),
    ]
)

ANALYSIS = AnalysisResult(
    belief_label="Under: Spending ≠ completion · v1",
    verdicts=[
        Verdict("Korea", "98%", "Success"),
        Verdict("Germany", "64%", "Not yet"),
        Verdict("Colombia", "78%", "Not yet"),
        Verdict("Nigeria", "—", "outside envelope", outside=True),
    ],
    traps=[
        Trap(
            entity="Germany",
            decoy_name="enrollment",
            decoy_label="103%",
            decoy_width="100%",
            primary_name="completion",
            primary_label="64%",
            primary_width="62%",
            unguided="“success”",
            believed="not yet",
        ),
    ],
    trap_count=7,
    thesis_note="your hypothesis, proven row by row: spend ≠ completion",
    receipt=Receipt(
        tokens=585,
        series=29,
        ungrounded_tokens=1399,
        ungrounded_series=86,
        ledger_row=4,
    ),
)

LEDGER = LedgerData(
    points=[
        LedgerPoint("ep 1", 1399, 1399),
        LedgerPoint("ep 2", 585, 1399),
        LedgerPoint("ep 3", 585, 1399),
        LedgerPoint("ep 4", 585, 1399),
        LedgerPoint("ep 5", 585, 1399),
        LedgerPoint("ep 6", 585, 1399),
        LedgerPoint("ep 7", 585, 1399),
        LedgerPoint("ep 8", 585, 1399),
        LedgerPoint("ep 9", 585, 1399),
        LedgerPoint("ep 10", 585, 1399),
    ],
    tiles=[
        Tile("run 2", "pack pays for itself", accent=True),
        Tile("−58%", "every run after"),
        Tile("7,249", "cumulative vs 13,990"),
    ],
    rows=[
        MemoryItem("row #4 · run", "585 tok · 100%"),
        MemoryItem("row #3 · re-run", "585 tok · auto"),
        MemoryItem("row #1 · cold", "1,399 tok · 71%"),
    ],
)

HISTORY = BeliefHistory(
    belief_name="Spending ≠ completion",
    version_label="Edit → v3",
    analysts=[
        Analyst("You", "", selected=True),
        Analyst("Maya", "effort belief"),
    ],
    events=[
        TimelineEvent(
            kind="data",
            title="Aug refresh — 214 new rows",
            note="re-ran automatically · 2 verdicts changed · meaning untouched",
        ),
        TimelineEvent(
            kind="belief",
            title="v2 — threshold tightened",
            when="Jul 2026",
            detail="High ≥ 85% → 90% → 3 countries changed verdict on the same data",
        ),
        TimelineEvent(
            kind="data",
            title="Run #2 — 24 verdicts",
            note="recalled v1 · 585 tokens",
        ),
        TimelineEvent(
            kind="belief",
            title="v1 — declared",
            when="Jun 2026",
            detail="“Government spending does not equal secondary completion.”",
        ),
    ],
    compare_note=(
        "Same data, two analysts, two beliefs — Maya's “effort” belief "
        "calls Germany a success; yours doesn't. Both provably right, each "
        "under its own belief."
    ),
)

BELIEFS = [
    MemoryItem(
        "Spending ≠ completion", "v1 · remembered", highlight=True, dataset_id="wdi"
    ),
    MemoryItem("Fiscal effort", "v1", dataset_id="fiscal"),
    MemoryItem("Export orientation", "v1", dataset_id="trade"),
]


def reply(msg: Any) -> Any:
    """Canned stand-in for the phase-2 actor replies."""
    match msg:
        case m.ListDatasets():
            return DATASETS
        case m.FetchColumns():
            return COLUMNS
        case m.RefreshDataset():
            return None  # a real refresh re-runs beliefs; nothing to fake here
        case m.DraftGrounding():
            return GROUNDING_DRAFT
        case m.RatifyBelief():
            # Writes are never demo-faked: a failed remember must surface as
            # a failure, not a fabricated "remembered" confirmation.
            return None
        case m.ListBeliefs():
            return BELIEFS
        case m.FetchBeliefHistory():
            return HISTORY
        case m.RunAnalysis():
            return ANALYSIS
        case m.FetchLedger():
            return LEDGER
    return None
